from __future__ import annotations

import logging

try:
    import nh3
except ImportError:
    nh3 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Safe tags permitted for HTML artifacts (rendered inside an isolated iframe sandbox)
ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "span", "strong", "table", "tbody", "td",
    "th", "thead", "tr", "ul", "section", "article", "header", "footer", "main", "button",
    "style",
}

ALLOWED_ATTRIBUTES = {
    "*": {"class", "id", "style", "title", "aria-*"},
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height"},
    "table": {"border", "cellpadding", "cellspacing"},
}


def sanitize_html(html: str) -> str:
    """Sanitize untrusted HTML before persistence/rendering.
    
    Provides defense-in-depth on the server before the client iframe sandbox:
    1. Removes all <script> and dangerous tags.
    2. Strips all inline event handlers (onerror, onclick, onload, etc.).
    3. Neutralizes javascript: pseudo-protocol URIs.
    """
    if not html:
        return ""

    if nh3 is not None:
        return nh3.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            url_schemes={"http", "https", "mailto", "data"},
        )

    # Fallback basic tag stripper if nh3 is unavailable in tests
    import re
    cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\bon\w+\s*=\s*['\"].*?['\"]", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"javascript:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned
