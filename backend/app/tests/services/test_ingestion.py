from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Chunk, Episode
from app.services import ingestion

FIXTURE_SLUGS = {"activation-expert", "retention-guru", "pricing-wizard", "teaser-guest", "no-frontmatter"}


async def _counts(factory: async_sessionmaker[AsyncSession]) -> tuple[int, int]:
    async with factory() as db:
        episodes = (await db.execute(select(func.count()).select_from(Episode))).scalar_one()
        chunks = (await db.execute(select(func.count()).select_from(Chunk))).scalar_one()
    return episodes, chunks


async def _episode(factory: async_sessionmaker[AsyncSession], slug: str) -> Episode:
    async with factory() as db:
        return (await db.execute(select(Episode).where(Episode.slug == slug))).scalar_one()


async def test_first_run_ingests_every_fixture(make_runner, transcripts_dir: Path, db_factory) -> None:
    stats = await make_runner(transcripts_dir).run("test")
    assert stats.files_found == 5
    assert stats.episodes_ingested == 5
    assert stats.episodes_skipped == 0
    assert stats.episodes_failed == 0
    episodes, chunks = await _counts(db_factory)
    assert episodes == 5
    assert chunks == stats.chunks_created >= 5


async def test_episode_metadata_is_stored(ingested, db_factory) -> None:
    episode = await _episode(db_factory, "activation-expert")
    assert episode.guest == "Ada Activation"
    assert episode.title.startswith("Ada Activation")
    assert episode.video_id == "ACT1VATE001"
    assert episode.youtube_url == "https://www.youtube.com/watch?v=ACT1VATE001"
    assert str(episode.publish_date) == "2023-03-14"
    assert episode.source_path == "episodes/activation-expert/transcript.md"
    assert len(episode.content_hash) == 64


async def test_file_with_missing_frontmatter_is_ingested_with_fallbacks(ingested, db_factory) -> None:
    episode = await _episode(db_factory, "no-frontmatter")
    assert episode.guest == "No Frontmatter"
    assert episode.title == "No Frontmatter"
    assert episode.youtube_url is None
    assert episode.publish_date is None
    teaser = await _episode(db_factory, "teaser-guest")
    assert teaser.guest == "Tess Teaser"
    assert teaser.title == "Tess Teaser"


async def test_chunks_have_text_speaker_timestamp_and_tsv(ingested, db_factory) -> None:
    async with db_factory() as db:
        row = (
            await db.execute(
                select(Chunk.text, Chunk.speaker, Chunk.start_seconds, Chunk.token_count)
                .join(Episode, Episode.id == Chunk.episode_id)
                .where(Episode.slug == "activation-expert")
                .order_by(Chunk.chunk_index)
            )
        ).first()
        assert row is not None
        chunk_text, speaker, start, tokens = row
        assert "Activation is the moment" in chunk_text
        assert speaker == "Lenny"
        assert start == 0
        assert tokens > 0
        matches = (
            await db.execute(
                text("SELECT count(*) FROM chunks WHERE tsv @@ websearch_to_tsquery('english', 'activation')")
            )
        ).scalar_one()
        assert matches >= 1


async def test_second_run_skips_everything(make_runner, transcripts_dir: Path, db_factory) -> None:
    runner = make_runner(transcripts_dir)
    first = await runner.run("test")
    before = await _counts(db_factory)
    second = await runner.run("test")
    assert second.episodes_ingested == 0
    assert second.episodes_skipped == 5
    assert second.chunks_created == 0
    assert await _counts(db_factory) == before
    assert first.episodes_ingested == 5


async def test_changed_file_is_reingested_and_others_skipped(
    make_runner, transcripts_dir: Path, db_factory
) -> None:
    runner = make_runner(transcripts_dir)
    await runner.run("test")
    old = await _episode(db_factory, "pricing-wizard")
    path = transcripts_dir / "episodes" / "pricing-wizard" / "transcript.md"
    path.write_text(
        path.read_text() + "\nPriya Pricing (00:20:00): Freemium conversion funnels are worth modelling.\n"
    )
    stats = await runner.run("test")
    assert stats.episodes_ingested == 1
    assert stats.episodes_skipped == 4
    new = await _episode(db_factory, "pricing-wizard")
    assert new.id == old.id  # updated in place, not duplicated
    assert new.content_hash != old.content_hash
    async with db_factory() as db:
        joined = (
            await db.execute(
                select(func.string_agg(Chunk.text, " ")).where(Chunk.episode_id == new.id)
            )
        ).scalar_one()
    assert "Freemium conversion funnels" in joined
    assert (await _counts(db_factory))[0] == 5


async def test_changing_chunk_settings_reindexes(make_runner, transcripts_dir: Path) -> None:
    await make_runner(transcripts_dir).run("test")
    stats = await make_runner(transcripts_dir, chunk_overlap_tokens=10).run("test")
    assert stats.episodes_ingested == 5


async def test_deleted_file_removes_episode_and_its_chunks(
    make_runner, transcripts_dir: Path, db_factory
) -> None:
    runner = make_runner(transcripts_dir)
    await runner.run("test")
    victim = await _episode(db_factory, "retention-guru")
    (transcripts_dir / "episodes" / "retention-guru" / "transcript.md").unlink()
    stats = await runner.run("test")
    assert stats.episodes_deleted == 1
    assert stats.episodes_skipped == 4
    async with db_factory() as db:
        gone = (await db.execute(select(Episode).where(Episode.slug == "retention-guru"))).first()
        orphans = (
            await db.execute(select(func.count()).select_from(Chunk).where(Chunk.episode_id == victim.id))
        ).scalar_one()
    assert gone is None
    assert orphans == 0


async def test_one_bad_file_does_not_stop_the_run(
    make_runner, transcripts_dir: Path, db_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_parse = ingestion.parse_transcript

    def flaky(raw: str, slug: str):  # type: ignore[no-untyped-def]
        if slug == "pricing-wizard":
            raise ValueError("boom")
        return real_parse(raw, slug)

    monkeypatch.setattr(ingestion, "parse_transcript", flaky)
    runner = make_runner(transcripts_dir)
    stats = await runner.run("test")
    assert stats.episodes_failed == 1
    assert stats.episodes_ingested == 4
    assert stats.errors[0].slug == "pricing-wizard"
    assert "boom" in stats.errors[0].message
    assert (await _counts(db_factory))[0] == 4

    # Next run (parser healthy again) picks up the failed file.
    monkeypatch.setattr(ingestion, "parse_transcript", real_parse)
    retry = await runner.run("test")
    assert retry.episodes_ingested == 1
    assert retry.episodes_skipped == 4


async def test_missing_directory_reports_failure_without_raising(make_runner, tmp_path: Path) -> None:
    runner = make_runner(tmp_path / "does-not-exist")
    await runner.run("test")
    status = await runner.snapshot()
    assert status.state == "failed"
    assert "not found" in (status.message or "")


async def test_empty_directory_never_wipes_existing_episodes(
    make_runner, transcripts_dir: Path, db_factory, tmp_path: Path
) -> None:
    await make_runner(transcripts_dir).run("test")
    empty = tmp_path / "empty"
    empty.mkdir()
    await make_runner(empty).run("test")
    assert (await _counts(db_factory))[0] == 5


async def test_long_episode_is_split_into_multiple_chunks(
    make_runner, tmp_path: Path, db_factory
) -> None:
    root = tmp_path / "t" / "episodes" / "long-one"
    root.mkdir(parents=True)
    turns = "\n\n".join(
        f"Guest ({i // 60:02d}:{i % 60:02d}:00): " + " ".join(f"word{j}" for j in range(120)) + "."
        for i in range(30)
    )
    (root / "transcript.md").write_text(f"---\nguest: Long One\n---\n{turns}\n")
    stats = await make_runner(tmp_path / "t").run("test")
    assert stats.chunks_created > 5
    async with db_factory() as db:
        indexes = (await db.execute(select(Chunk.chunk_index).order_by(Chunk.chunk_index))).scalars().all()
    assert list(indexes) == list(range(stats.chunks_created))


async def test_status_reports_counts_and_totals(make_runner, transcripts_dir: Path) -> None:
    runner = make_runner(transcripts_dir)
    assert (await runner.snapshot()).state == "idle"
    await runner.run("startup")
    status = await runner.snapshot()
    assert status.state == "completed"
    assert status.trigger == "startup"
    assert status.episodes_ingested == 5
    assert status.total_episodes == 5
    assert status.total_chunks == status.chunks_created
    assert status.started_at and status.finished_at


async def test_start_runs_in_background_and_wait_completes(make_runner, transcripts_dir: Path) -> None:
    runner = make_runner(transcripts_dir)
    assert runner.start("manual") is True
    await runner.wait()
    assert (await runner.snapshot()).state == "completed"
