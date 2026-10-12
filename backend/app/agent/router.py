from __future__ import annotations

import re

_ESSAY_KEYWORDS = re.compile(
    r"\b(essay|atomic\s*essay|ship\s*30|ship30|(?:write|draft)\s+an?\s+(?:article|post|guide|essay)|deep\s+dive\s+guide|newsletter\s+edition)\b",
    re.IGNORECASE,
)
_ARTIFACT_KEYWORDS = re.compile(
    r"\b(html|landing\s+page|widget|ui\s+component|calculator|interactive\s+calculator|css|snippet|code\s+artifact)\b",
    re.IGNORECASE,
)


def classify_intent(content: str, explicit_intent: str | None = None) -> str:
    """Classify the user message into 'qa', 'essay', or 'artifact'."""
    if explicit_intent in ("qa", "essay", "artifact"):
        return explicit_intent

    text = content.strip().lower()
    if _ESSAY_KEYWORDS.search(text):
        return "essay"
    if _ARTIFACT_KEYWORDS.search(text):
        return "artifact"
    return "qa"
