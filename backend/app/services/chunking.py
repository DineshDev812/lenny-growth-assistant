"""Split dialogue turns into ~400-500 token chunks along speaker turns.

Token counts are estimated (about 1.33 tokens per word) so no tokenizer
dependency is needed. Each chunk keeps the start timestamp of its first
segment, and consecutive chunks share a small overlap.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.services.transcript_parser import Turn

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    text: str
    speaker: str | None
    start_seconds: int | None
    token_count: int


@dataclass(frozen=True)
class _Segment:
    speaker: str | None
    start_seconds: int | None
    text: str
    tokens: int


def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return math.ceil(words * 1.33) if words else 0


def _render(segment: _Segment) -> str:
    return f"{segment.speaker}: {segment.text}" if segment.speaker else segment.text


def _make(speaker: str | None, start: int | None, text: str) -> _Segment:
    """Build a segment whose token count includes its rendered speaker label."""
    return _Segment(speaker, start, text, estimate_tokens(_render(_Segment(speaker, start, text, 0))))


def _split_long_text(text: str, max_tokens: int) -> list[str]:
    """Break text that exceeds max_tokens on sentence ends, then on words."""
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in _SENTENCE_RE.split(text):
        words = sentence.split()
        if not words:
            continue
        sentence_tokens = estimate_tokens(sentence)
        if sentence_tokens > max_tokens:
            if current:
                pieces.append(" ".join(current))
                current, current_tokens = [], 0
            step = max(1, int(max_tokens / 1.33))
            for index in range(0, len(words), step):
                pieces.append(" ".join(words[index : index + step]))
            continue
        if current and current_tokens + sentence_tokens > max_tokens:
            pieces.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        pieces.append(" ".join(current))
    return pieces


def _to_segments(turns: list[Turn], max_tokens: int) -> list[_Segment]:
    segments: list[_Segment] = []
    for turn in turns:
        text = turn.text.strip()
        if not text:
            continue
        if _make(turn.speaker, turn.start_seconds, text).tokens <= max_tokens:
            segments.append(_make(turn.speaker, turn.start_seconds, text))
            continue
        for piece in _split_long_text(text, max_tokens):
            segments.append(_make(turn.speaker, turn.start_seconds, piece))
    return segments


def _overlap_tail(segments: list[_Segment], overlap_tokens: int) -> list[_Segment]:
    """Trailing segments (or a word-tail of the last one) worth ~overlap_tokens."""
    if overlap_tokens <= 0 or not segments:
        return []
    tail: list[_Segment] = []
    total = 0
    for segment in reversed(segments):
        if total + segment.tokens > overlap_tokens:
            break
        tail.insert(0, segment)
        total += segment.tokens
    if tail:
        return tail
    last = segments[-1]
    words = last.text.split()
    keep = max(1, int(overlap_tokens / 1.33))
    if len(words) <= keep:
        return [last]
    text = " ".join(words[-keep:])
    return [_make(last.speaker, last.start_seconds, text)]


def _label_cost(segment: _Segment) -> int:
    return estimate_tokens(segment.speaker) if segment.speaker else 0


def _split_head(segment: _Segment, room_tokens: int) -> tuple[_Segment, _Segment] | None:
    """Split a segment so the head fits room_tokens; None if nothing sensible fits."""
    head: list[str] = []
    used = 0
    sentences = [part for part in _SENTENCE_RE.split(segment.text) if part.strip()]
    for position, sentence in enumerate(sentences):
        cost = estimate_tokens(sentence)
        if used + cost + _label_cost(segment) > room_tokens:
            if not head:
                return None
            rest_text = " ".join(sentences[position:])
            head_text = " ".join(head)
            return (
                _make(segment.speaker, segment.start_seconds, head_text),
                _make(segment.speaker, segment.start_seconds, rest_text),
            )
        head.append(sentence)
        used += cost
    return None


def _build(index: int, segments: list[_Segment]) -> ChunkDraft:
    text = "\n\n".join(_render(segment) for segment in segments)
    return ChunkDraft(
        chunk_index=index,
        text=text,
        speaker=segments[0].speaker,
        start_seconds=segments[0].start_seconds,
        token_count=estimate_tokens(text),
    )


def chunk_turns(
    turns: list[Turn],
    *,
    target_tokens: int = 450,
    max_tokens: int = 500,
    overlap_tokens: int = 60,
) -> list[ChunkDraft]:
    """Greedy packing: fill toward target_tokens, never exceed max_tokens."""
    max_tokens = max(max_tokens, target_tokens)
    overlap_tokens = min(overlap_tokens, max_tokens // 4)
    segments = _to_segments(turns, max_tokens - overlap_tokens - 8)
    chunks: list[ChunkDraft] = []
    buffer: list[_Segment] = []
    buffer_tokens = 0
    fresh = 0  # segments in buffer that are new (not carried-over overlap)

    queue = list(reversed(segments))
    min_fill = max(target_tokens - 50, 0)
    while queue:
        segment = queue.pop()
        would_exceed = buffer_tokens + segment.tokens > max_tokens
        if would_exceed and fresh and buffer_tokens < min_fill:
            split = _split_head(segment, max_tokens - buffer_tokens)
            if split is not None:
                head, rest = split
                queue.append(rest)
                segment = head
                would_exceed = False
        reached_target = buffer_tokens >= target_tokens
        if fresh and (would_exceed or reached_target):
            chunks.append(_build(len(chunks), buffer))
            buffer = _overlap_tail(buffer, overlap_tokens)
            buffer_tokens = sum(item.tokens for item in buffer)
            fresh = 0
            if buffer_tokens + segment.tokens > max_tokens:
                buffer, buffer_tokens = [], 0
        buffer.append(segment)
        buffer_tokens += segment.tokens
        fresh += 1
    if fresh:
        chunks.append(_build(len(chunks), buffer))
    return chunks
