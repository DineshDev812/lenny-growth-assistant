"""Parse a transcript.md file: YAML frontmatter plus timestamped dialogue turns.

Pure functions only (no database, no I/O) so they are easy to test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A﻿?\s*---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_TURN_RE = re.compile(
    r"^[ \t]*(?:\*\*|__)?(?P<speaker>[^\n()\[\]:]{1,80}?)(?:\*\*|__)?"
    r"[ \t]*\((?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\)[ \t]*:?(?:\*\*|__)?[ \t]*(?P<rest>.*)$"
)
_SLUG_SPLIT_RE = re.compile(r"[-_]+")


@dataclass(frozen=True)
class Turn:
    speaker: str | None
    start_seconds: int | None
    text: str


@dataclass
class ParsedTranscript:
    slug: str
    guest: str
    title: str
    youtube_url: str | None = None
    video_id: str | None = None
    publish_date: date | None = None
    description: str | None = None
    keywords: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def slug_to_name(slug: str) -> str:
    parts = [part for part in _SLUG_SPLIT_RE.split(slug) if part]
    return " ".join(part.capitalize() for part in parts) or slug


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str, list[str]]:
    """Return (metadata, body, warnings). Never raises on malformed input."""
    warnings: list[str] = []
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw.lstrip("﻿"), ["no frontmatter block found"]
    block = match.group(1)
    body = raw[match.end():]
    try:
        loaded = yaml.safe_load(block)
        if isinstance(loaded, dict):
            return loaded, body, warnings
        warnings.append("frontmatter is not a mapping; used line fallback")
    except yaml.YAMLError:
        warnings.append("invalid YAML frontmatter; used line fallback")
    return _fallback_frontmatter(block), body, warnings


def _fallback_frontmatter(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        key = key.strip()
        if not sep or not key or " " in key:
            continue
        data[key] = value.strip().strip("\"'")
    return data


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return None
    text = str(value).strip()
    return text or None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _as_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text[:40], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _as_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        items = [str(part).strip() for part in value]
    else:
        return []
    return [item for item in items if item]


def timestamp_to_seconds(ts: str) -> int:
    parts = [int(part) for part in ts.split(":")]
    if len(parts) == 2:
        parts = [0, *parts]
    hours, minutes, seconds = parts
    return hours * 3600 + minutes * 60 + seconds


def format_timestamp(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    hours, rest = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_turns(body: str) -> list[Turn]:
    """Split dialogue into turns on lines like `Name (00:01:02): text`.

    Text before the first speaker line, or a body with no speaker lines at all,
    becomes one turn without a speaker or timestamp.
    """
    turns: list[Turn] = []
    speaker: str | None = None
    start: int | None = None
    buffer: list[str] = []
    seen_turn = False

    def flush() -> None:
        text = " ".join(part.strip() for part in buffer if part.strip()).strip()
        if text:
            turns.append(Turn(speaker=speaker, start_seconds=start, text=text))

    for line in body.splitlines():
        match = _TURN_RE.match(line)
        if match:
            flush()
            buffer = []
            seen_turn = True
            speaker = match.group("speaker").strip(" *_") or None
            start = timestamp_to_seconds(match.group("ts"))
            rest = match.group("rest").strip()
            if rest:
                buffer.append(rest)
        else:
            buffer.append(line)
    flush()
    if not seen_turn and not turns:
        return []
    return turns


def parse_transcript(raw: str, slug: str) -> ParsedTranscript:
    metadata, body, warnings = split_frontmatter(raw)
    guest = _as_text(metadata.get("guest")) or slug_to_name(slug)
    title = _as_text(metadata.get("title")) or guest
    if not _as_text(metadata.get("guest")):
        warnings.append("missing guest; derived from slug")
    if not _as_text(metadata.get("title")):
        warnings.append("missing title; used guest")
    youtube_url = _as_text(metadata.get("youtube_url"))
    video_id = _as_text(metadata.get("video_id"))
    if not youtube_url and video_id:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    turns = parse_turns(body)
    if not turns:
        text = " ".join(body.split())
        if text:
            turns = [Turn(speaker=None, start_seconds=None, text=text)]
            warnings.append("no timestamped speaker lines; treated body as one block")
        else:
            warnings.append("empty transcript body")
    return ParsedTranscript(
        slug=slug,
        guest=guest,
        title=title,
        youtube_url=youtube_url,
        video_id=video_id,
        publish_date=_as_date(metadata.get("publish_date")),
        description=_as_text(metadata.get("description")),
        keywords=_as_keywords(metadata.get("keywords")),
        turns=turns,
        warnings=warnings,
    )
