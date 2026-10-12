from __future__ import annotations

import re

# Pronouns indicating reference to previous turn
_PRONOUNS_RE = re.compile(
    r"\b(it|that|this|he|she|they|his|her|their|them)\b",
    re.IGNORECASE,
)

# Follow-up start phrases
_START_FOLLOW_UP_RE = re.compile(
    r"^(and|what about|how about)\b",
    re.IGNORECASE,
)

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

COMMON_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what", "which", "who", "whom",
    "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "would", "should", "could",
    "ought", "i", "you", "he", "she", "it", "we", "they", "them", "their", "theirs", "our",
    "ours", "your", "yours", "my", "mine", "his", "her", "hers", "its", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after", "above", "below", "to",
    "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "dont", "shouldnt", "cant",
    "without", "conduct", "employed", "using", "use", "used", "make", "made",
    "by", "of", "tell", "me", "more", "like", "say", "said", "says",
}


def is_follow_up(text: str) -> bool:
    """Determine whether a query is a conversational follow-up needing prior context."""
    words = text.strip().split()
    if len(words) < 5:
        return True
    if _PRONOUNS_RE.search(text):
        return True
    if _START_FOLLOW_UP_RE.search(text.strip()):
        return True
    return False


def extract_salient_terms(text: str, max_terms: int = 6) -> list[str]:
    """Extract salient, informative, non-stopword tokens in order of appearance."""
    seen: dict[str, None] = {}
    for token in _WORD_RE.findall(text.lower()):
        if len(token) >= 3 and token not in COMMON_STOPWORDS:
            seen.setdefault(token, None)
            if len(seen) >= max_terms:
                break
    return list(seen.keys())


def build_retrieval_query(
    current_message: str,
    previous_user_message: str | None = None,
    max_chars: int = 500,
) -> str:
    """Build a search query enriched with prior context if current turn is a follow-up.

    Caps total query at max_chars (default 500). Pure function, zero LLM calls.
    """
    clean_curr = " ".join(current_message.strip().split())
    if not clean_curr:
        return ""

    if previous_user_message and is_follow_up(clean_curr):
        terms = extract_salient_terms(previous_user_message, max_terms=6)
        if terms:
            enriched = f"{clean_curr} {' '.join(terms)}"
            return enriched[:max_chars].strip()

    return clean_curr[:max_chars].strip()
