from __future__ import annotations

import re

_SMALLTALK_GREETING_RE = re.compile(
    r"^(hi|hello|hey|hey\s+there|howdy|sup|yo|good\s+(?:morning|afternoon|evening)|greetings)[!.,?\s]*$",
    re.IGNORECASE,
)
_SMALLTALK_THANKS_RE = re.compile(
    r"^(thanks|thank\s+you|thx|ty|many\s+thanks|appreciate\s+it|thank\s+you\s+so\s+much|thanks\s+a\s+lot)[!.,?\s]*$",
    re.IGNORECASE,
)
_SMALLTALK_IDENTITY_RE = re.compile(
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|what\s+are\s+you|help|who\s+made\s+you|who\s+created\s+you|what\s+is\s+your\s+name|how\s+can\s+you\s+help)[!.,?\s]*$",
    re.IGNORECASE,
)

_ESSAY_KEYWORDS = re.compile(
    r"\b(essay|atomic\s*essay|ship\s*30|ship30|(?:write|draft)\s+an?\s+(?:article|post|guide|essay)|deep\s+dive\s+guide|newsletter\s+edition)\b",
    re.IGNORECASE,
)
_ARTIFACT_KEYWORDS = re.compile(
    r"\b(html|landing\s+page|widget|ui\s+component|calculator|interactive\s+calculator|css|code\s+artifact)\b",
    re.IGNORECASE,
)

_DOMAIN_KEYWORDS = re.compile(
    r"\b(product|growth|retention|activation|pricing|pmf|product-market\s+fit|onboarding|roadmap|startup|startups|"
    r"founder|founders|pm|pms|product\s+manager|product\s+management|metrics|experiment|experimentation|marketing|"
    r"hiring|ltv|cac|churn|b2b|b2c|plg|product-led|sales-led|nrr|marketplace|marketplaces|flywheel|funnel|funnels|"
    r"conversion|virality|viral\s+loop|brian\s+chesky|lenny|shreyas|elena\s+verna|casey\s+winters|patrick\s+campbell|"
    r"gustaf\s+alströmer|unit\s+economics|north\s+star|network\s+effects?|cohorts?|distribution|customer\s+acquisition|"
    r"figma|users?|customers?|podcast|guests?|interview)\b",
    re.IGNORECASE,
)


def is_smalltalk(text: str) -> bool:
    cleaned = text.strip()
    return bool(
        _SMALLTALK_GREETING_RE.match(cleaned)
        or _SMALLTALK_THANKS_RE.match(cleaned)
        or _SMALLTALK_IDENTITY_RE.match(cleaned)
    )


def classify_intent(content: str, explicit_intent: str | None = None) -> str:
    """Classify user intent into 'qa', 'essay', 'artifact', or 'general'."""
    if explicit_intent in ("qa", "essay", "artifact", "general"):
        return explicit_intent

    text = content.strip().lower()
    if _ESSAY_KEYWORDS.search(text):
        return "essay"
    if _ARTIFACT_KEYWORDS.search(text):
        return "artifact"
    return "qa"


def classify_route(content: str, explicit_intent: str | None = None) -> str:
    """Classify query into execution route:
    'smalltalk', 'essay', 'artifact', 'grounded', or 'general'.
    """
    if explicit_intent == "general":
        return "general"
    if explicit_intent == "essay":
        return "essay"
    if explicit_intent == "artifact":
        return "artifact"

    text = content.strip()
    if not text:
        return "grounded"

    if is_smalltalk(text):
        return "smalltalk"

    text_lower = text.lower()
    if _ESSAY_KEYWORDS.search(text_lower):
        return "essay"
    if _ARTIFACT_KEYWORDS.search(text_lower):
        return "artifact"

    if explicit_intent == "qa":
        return "grounded"

    if _DOMAIN_KEYWORDS.search(text_lower):
        return "grounded"

    # Non-domain queries (cooking, sports, code, trivia, math) route to general
    return "general"
