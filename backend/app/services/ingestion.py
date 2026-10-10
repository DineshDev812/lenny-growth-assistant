"""Idempotent transcript ingestion.

One `IngestRunner` lives on `app.state`. It scans the transcripts folder, skips files whose
content hash is unchanged, re-ingests changed files, removes episodes whose file was deleted,
and isolates failures per file so one bad file never stops the run.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.repositories.episodes import EpisodeRepository
from app.schemas.ingest import IngestErrorItem, IngestStatusResponse
from app.services.chunking import chunk_turns
from app.services.transcript_parser import parse_transcript

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]
MAX_RECORDED_ERRORS = 25


@dataclass
class IngestStats:
    files_found: int = 0
    episodes_ingested: int = 0
    episodes_skipped: int = 0
    episodes_failed: int = 0
    episodes_deleted: int = 0
    chunks_created: int = 0
    errors: list[IngestErrorItem] = field(default_factory=list)


@dataclass
class _State:
    state: str = "idle"
    trigger: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None
    stats: IngestStats = field(default_factory=IngestStats)


def discover_transcripts(root: Path) -> dict[str, Path]:
    """Map slug -> transcript.md path. Supports root/episodes/{slug}/ and root/{slug}/."""
    base = root / "episodes" if (root / "episodes").is_dir() else root
    found: dict[str, Path] = {}
    for path in sorted(base.glob("*/transcript.md")):
        if path.is_file():
            found[path.parent.name] = path
    return found


def hash_content(raw: bytes, *, settings: Settings) -> str:
    """Hash file bytes plus chunking settings, so changing chunk sizes re-indexes everything."""
    salt = f"v1:{settings.chunk_target_tokens}:{settings.chunk_max_tokens}:{settings.chunk_overlap_tokens}\n"
    return hashlib.sha256(salt.encode() + raw).hexdigest()


class IngestRunner:
    def __init__(self, session_factory: SessionFactory, settings: Settings) -> None:
        self._factory = session_factory
        self._settings = settings
        self._state = _State()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    # -- control -----------------------------------------------------------------------
    def start(self, trigger: str) -> bool:
        """Start a background run. Returns False if one is already running."""
        if self.is_running or (self._task is not None and not self._task.done()):
            return False
        self._begin(trigger)  # state is "running" immediately, before the task is scheduled
        self._task = asyncio.create_task(self._background(), name=f"ingest-{trigger}")
        return True

    async def wait(self) -> None:
        task = self._task
        if task is not None:
            await asyncio.shield(task)

    async def shutdown(self) -> None:
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    @property
    def is_running(self) -> bool:
        return self._state.state == "running"

    async def snapshot(self) -> IngestStatusResponse:
        state = self._state
        stats = state.stats
        total_episodes: int | None = None
        total_chunks: int | None = None
        try:
            async with self._factory() as db:
                repo = EpisodeRepository(db)
                total_episodes = await repo.count_episodes()
                total_chunks = await repo.count_chunks()
        except Exception:  # noqa: BLE001 - status must never fail because the DB is down
            logger.warning("Could not read ingest totals", extra={"event": "ingest_totals_failed"})
        return IngestStatusResponse(
            state=state.state,  # type: ignore[arg-type]
            trigger=state.trigger,
            started_at=state.started_at,
            finished_at=state.finished_at,
            transcripts_dir=self._settings.transcripts_dir,
            files_found=stats.files_found,
            episodes_ingested=stats.episodes_ingested,
            episodes_skipped=stats.episodes_skipped,
            episodes_failed=stats.episodes_failed,
            episodes_deleted=stats.episodes_deleted,
            chunks_created=stats.chunks_created,
            total_episodes=total_episodes,
            total_chunks=total_chunks,
            errors=list(stats.errors),
            message=state.message,
        )

    # -- the run -----------------------------------------------------------------------
    def _begin(self, trigger: str) -> None:
        self._state = _State(
            state="running",
            trigger=trigger,
            started_at=datetime.now(timezone.utc),
            stats=IngestStats(),
        )

    async def _background(self) -> None:
        async with self._lock:
            await self._execute()

    async def run(self, trigger: str = "manual") -> IngestStats:
        """Run ingestion now and wait for it (used directly by tests; the API uses start())."""
        async with self._lock:
            self._begin(trigger)
            return await self._execute()

    async def _execute(self) -> IngestStats:
        stats = self._state.stats
        began = time.perf_counter()
        logger.info("Ingestion started", extra={"event": "ingest_started"})
        try:
            await self._ingest_all(stats)
            self._state.state = "completed" if self._state.message is None else "failed"
        except asyncio.CancelledError:
            self._state.state = "failed"
            self._state.message = "Ingestion was cancelled."
            raise
        except Exception as exc:  # noqa: BLE001 - never let the background task crash the app
            logger.exception("Ingestion run failed", extra={"event": "ingest_failed"})
            self._state.state = "failed"
            self._state.message = f"Ingestion failed: {exc}"
        finally:
            self._state.finished_at = datetime.now(timezone.utc)
        elapsed_ms = round((time.perf_counter() - began) * 1000)
        logger.info(
            "Ingestion finished: ingested=%d skipped=%d failed=%d deleted=%d chunks_created=%d (%d ms)"
            % (
                stats.episodes_ingested,
                stats.episodes_skipped,
                stats.episodes_failed,
                stats.episodes_deleted,
                stats.chunks_created,
                elapsed_ms,
            ),
            extra={
                "event": "ingest_finished",
                "episodes_ingested": stats.episodes_ingested,
                "episodes_skipped": stats.episodes_skipped,
                "episodes_failed": stats.episodes_failed,
                "episodes_deleted": stats.episodes_deleted,
                "chunks_created": stats.chunks_created,
                "latency_ms": elapsed_ms,
            },
        )
        return stats

    async def _ingest_all(self, stats: IngestStats) -> None:
        root = Path(self._settings.transcripts_dir)
        if not root.is_dir():
            self._state.message = f"Transcripts directory not found: {root}"
            logger.warning(self._state.message, extra={"event": "ingest_no_directory"})
            return
        files = await asyncio.to_thread(discover_transcripts, root)
        stats.files_found = len(files)
        if not files:
            self._state.message = f"No transcript.md files found under {root}"
            logger.warning(self._state.message, extra={"event": "ingest_no_files"})
            return

        async with self._factory() as db:
            known_hashes = await EpisodeRepository(db).hashes_by_slug()

        for slug, path in files.items():
            try:
                await self._ingest_one(slug, path, root, known_hashes.get(slug), stats)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - one bad file must not stop the run
                stats.episodes_failed += 1
                logger.error(
                    "Failed to ingest %s: %s" % (slug, exc),
                    extra={"event": "ingest_file_failed", "error_class": type(exc).__name__},
                )
                if len(stats.errors) < MAX_RECORDED_ERRORS:
                    stats.errors.append(IngestErrorItem(slug=slug, message=f"{type(exc).__name__}: {exc}"))

        missing = sorted(set(known_hashes) - set(files))
        if missing:
            try:
                async with self._factory() as db:
                    async with db.begin():
                        stats.episodes_deleted = await EpisodeRepository(db).delete_by_slugs(missing)
                logger.info(
                    "Removed %d episodes whose transcript file no longer exists" % stats.episodes_deleted,
                    extra={"event": "ingest_deleted"},
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to remove deleted episodes: %s" % exc, extra={"event": "ingest_delete_failed"})
                if len(stats.errors) < MAX_RECORDED_ERRORS:
                    stats.errors.append(IngestErrorItem(slug="*", message=f"delete failed: {exc}"))

    async def _ingest_one(
        self,
        slug: str,
        path: Path,
        root: Path,
        known_hash: str | None,
        stats: IngestStats,
    ) -> None:
        raw = await asyncio.to_thread(path.read_bytes)
        digest = hash_content(raw, settings=self._settings)
        if known_hash == digest:
            stats.episodes_skipped += 1
            return

        parsed = parse_transcript(raw.decode("utf-8", errors="replace").replace("\x00", ""), slug)
        for warning in parsed.warnings:
            logger.info("%s: %s" % (slug, warning), extra={"event": "ingest_warning"})
        drafts = chunk_turns(
            parsed.turns,
            target_tokens=self._settings.chunk_target_tokens,
            max_tokens=self._settings.chunk_max_tokens,
            overlap_tokens=self._settings.chunk_overlap_tokens,
        )
        chunk_rows = [
            {
                "chunk_index": draft.chunk_index,
                "text": draft.text,
                "speaker": draft.speaker,
                "start_seconds": draft.start_seconds,
                "token_count": draft.token_count,
            }
            for draft in drafts
        ]
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        async with self._factory() as db:
            async with db.begin():
                created = await EpisodeRepository(db).replace_episode(
                    slug=slug,
                    guest=parsed.guest,
                    title=parsed.title,
                    youtube_url=parsed.youtube_url,
                    video_id=parsed.video_id,
                    publish_date=parsed.publish_date,
                    description=parsed.description,
                    source_path=relative,
                    content_hash=digest,
                    chunks=chunk_rows,
                )
        stats.episodes_ingested += 1
        stats.chunks_created += created
