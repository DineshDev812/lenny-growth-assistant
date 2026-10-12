from __future__ import annotations

import re
from typing import Sequence
from uuid import UUID

from app.schemas.messages import Source
from app.schemas.retrieval import RetrievedChunk
from app.services.transcript_parser import format_timestamp

# Matches citation groups like:
# [S1], [s1], [S1, S2], [S1,S2], [S1; S2], [S1, S2, S3]
# Notice: Does NOT match bare numbers like [1], [2], [2023] because of the mandatory 's' or 'S'.
_CITATION_GROUP_RE = re.compile(
    r"\[\s*([sS]\d+(?:\s*[,;]\s*[sS]\d+)*)\s*\]"
)
_SINGLE_S_RE = re.compile(r"[sS](\d+)")

# Markdown link: [text](url)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)")
# Bare URL
_BARE_URL_RE = re.compile(r"(?<!\()(https?://[^\s\)]+)")


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    return url.strip().rstrip("/")


def validate_citations(
    text: str,
    sources: Sequence[Source],
) -> tuple[str, list[str], list[str]]:
    """Validate and normalize citation markers in text against retrieved sources.

    - Matches [S1], [s1], [S1, S2], [S1][S2] (case-insensitive 'S').
    - Does NOT touch bare [1], [2023], etc.
    - Normalizes multi-markers: [S1, S2] -> [S1][S2].
    - Drops citation IDs that do not exist in the retrieved sources.
    - Strips hallucinated URLs not present in the retrieved sources.
    - Returns (clean_text, used_ids_in_order, dropped_ids).
    """
    valid_source_ids = {s.id.upper() for s in sources}

    # Collect allowed URLs (both base youtube_url and deep links)
    allowed_urls: set[str] = set()
    for s in sources:
        if s.youtube_url:
            allowed_urls.add(_normalize_url(s.youtube_url))
        if s.youtube_deep_link:
            allowed_urls.add(_normalize_url(s.youtube_deep_link))

    used_ids_in_order: list[str] = []
    dropped_ids: list[str] = []
    seen_used: set[str] = set()

    def replace_citation_group(match: re.Match[str]) -> str:
        group_content = match.group(1)
        found_nums = _SINGLE_S_RE.findall(group_content)
        valid_in_group: list[str] = []

        for num in found_nums:
            canonical = f"S{num}"
            if canonical in valid_source_ids:
                valid_in_group.append(canonical)
                if canonical not in seen_used:
                    seen_used.add(canonical)
                    used_ids_in_order.append(canonical)
            else:
                if canonical not in dropped_ids:
                    dropped_ids.append(canonical)

        if not valid_in_group:
            return ""

        # Normalize to [S1][S2]...
        return "".join(f"[{cid}]" for cid in valid_in_group)

    # 1. Normalize and filter citations
    cleaned = _CITATION_GROUP_RE.sub(replace_citation_group, text)

    # Clean up any leftover whitespace from completely dropped citations
    cleaned = re.sub(r" +([.,!?;])", r"\1", cleaned)
    cleaned = re.sub(r"  +", " ", cleaned)

    # 2. Strip hallucinated URLs
    def replace_md_link(match: re.Match[str]) -> str:
        anchor_text = match.group(1)
        url = match.group(2)
        norm = _normalize_url(url)
        if norm in allowed_urls:
            return match.group(0)
        # Drop hallucinated link target, keep anchor text
        return anchor_text

    cleaned = _MD_LINK_RE.sub(replace_md_link, cleaned)

    def replace_bare_url(match: re.Match[str]) -> str:
        url = match.group(1)
        norm = _normalize_url(url)
        if norm in allowed_urls:
            return match.group(0)
        # Drop hallucinated bare URL
        return ""

    cleaned = _BARE_URL_RE.sub(replace_bare_url, cleaned)
    cleaned = re.sub(r"  +", " ", cleaned)

    return cleaned, used_ids_in_order, dropped_ids


def filter_cited_sources(
    sources: Sequence[Source],
    used_ids: Sequence[str],
) -> list[Source]:
    """Return only sources whose IDs appear in used_ids, preserving original IDs."""
    used_set = {uid.upper() for uid in used_ids}
    return [s for s in sources if s.id.upper() in used_set]


def escape_chunk_text(text: str) -> str:
    """Escape angle brackets to defend against prompt injection inside transcript quotes."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def format_source_context(
    chunks: list[RetrievedChunk],
    *,
    token_budget: int = 3000,
    max_chunks_per_episode: int = 2,
) -> tuple[list[Source], str]:
    """Filter chunks by budget and per-episode cap, formatting into safe delimited sources.

    Delimiters: <source id="S1" ...>...</source>
    """
    sources: list[Source] = []
    xml_blocks: list[str] = []
    episode_counts: dict[UUID, int] = {}
    estimated_tokens_used = 0

    idx = 1
    for chunk in chunks:
        # At most 2 chunks per episode
        ep_count = episode_counts.get(chunk.episode_id, 0)
        if ep_count >= max_chunks_per_episode:
            continue

        # Rough token estimate: ~4 chars per token
        chunk_token_est = len(chunk.text) // 4 + 50
        if estimated_tokens_used + chunk_token_est > token_budget and sources:
            # Budget exhausted, stop adding chunks
            break

        episode_counts[chunk.episode_id] = ep_count + 1
        estimated_tokens_used += chunk_token_est

        sid = f"S{idx}"
        idx += 1

        snippet = " ".join(chunk.text.split())[:300]
        s = Source(
            id=sid,
            chunk_id=chunk.chunk_id,
            episode_id=chunk.episode_id,
            slug=chunk.episode_slug,
            title=chunk.episode_title,
            guest=chunk.guest,
            publish_date=str(chunk.publish_date) if chunk.publish_date else None,
            youtube_url=chunk.youtube_url,
            youtube_deep_link=chunk.youtube_deep_link or chunk.youtube_url,
            start_ts=chunk.start_timestamp,
            start_seconds=chunk.start_seconds,
            snippet=snippet,
        )
        sources.append(s)

        escaped = escape_chunk_text(chunk.text)
        time_str = chunk.start_timestamp or "N/A"
        xml_blocks.append(
            f'<source id="{sid}" episode="{chunk.episode_title}" guest="{chunk.guest}" time="{time_str}">\n'
            f"{escaped}\n"
            f"</source>"
        )

    return sources, "\n\n".join(xml_blocks)
