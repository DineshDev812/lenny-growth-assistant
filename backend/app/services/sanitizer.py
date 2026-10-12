from __future__ import annotations

import logging
import re

try:
    import nh3
except ImportError:
    nh3 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Safe structural and semantic tags permitted for HTML artifacts
ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "span", "strong", "table", "tbody", "td",
    "th", "thead", "tr", "ul", "section", "article", "header", "footer", "main", "dl", "dt", "dd",
}

# Explicitly disallowed: style, script, iframe, object, embed, form, input, button, svg, math, etc.

ALLOWED_ATTRIBUTES = {
    "*": {"class", "id", "title"},
    "a": {"href", "target"},
    "img": {"src", "alt", "width", "height"},
    "table": {"border", "cellpadding", "cellspacing"},
}

FALLBACK_SAFE_MESSAGE = "<p>Artifact content could not be displayed safely.</p>"

_FENCED_HTML_RE = re.compile(
    r"^[ \t]*```(?:html|xml)?[ \t]*\n([\s\S]*?)\n[ \t]*```",
    re.IGNORECASE | re.MULTILINE,
)
_FENCED_MD_RE = re.compile(
    r"^[ \t]*```(?:markdown|md)?[ \t]*\n([\s\S]*?)\n[ \t]*```",
    re.IGNORECASE | re.MULTILINE,
)


def sanitize_html(html: str) -> str:
    """Sanitize untrusted HTML before persistence/rendering.

    Defense-in-depth on the server before client sandbox:
    1. Only allows safe semantic tags. Strips <style>, <script>, <iframe>, <form>, <button>, <svg>, etc.
    2. Strips all inline event handlers ('on*') and 'style' attributes.
    3. Allows only http, https, mailto URL schemes (strictly NO data: or javascript:).
    4. Automatically enforces rel="noopener noreferrer" on all <a> tags.
    5. Fails closed with a safe notice if parsing fails.
    """
    if not html:
        return ""

    try:
        if nh3 is not None:
            return nh3.clean(
                html,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                url_schemes={"http", "https", "mailto"},
                link_rel="noopener noreferrer",
            )

        # Fallback regex sanitizer if nh3 is not installed
        cleaned = re.sub(
            r"<\s*(style|script|iframe|object|embed|form|input|button|svg|math)[^>]*>.*?<\s*/\s*\1\s*>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cleaned = re.sub(
            r"<\s*(style|script|iframe|object|embed|form|input|button|svg|math)[^>]*/*>",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bon\w+\s*=\s*['\"].*?['\"]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bstyle\s*=\s*['\"].*?['\"]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"javascript:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"data:\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned
    except Exception as exc:
        logger.warning("HTML sanitization failed: %s; failing closed", exc)
        return FALLBACK_SAFE_MESSAGE


def extract_artifact_content(raw_text: str, format: str) -> str:
    """Extract code block from model response or wrap in clean HTML boilerplate.

    - If a fenced ```html or ```markdown block is found, extracts the first block.
    - If no block is found:
      - For HTML: wraps in safe minimal boilerplate and sanitizes.
      - For Markdown: takes raw text.
    """
    fmt = format.lower().strip()
    text = raw_text.strip()

    if fmt == "html":
        match = _FENCED_HTML_RE.search(text)
        if match:
            block = match.group(1).strip()
            return sanitize_html(block)
        # Wrap bare text in boilerplate
        boilerplate = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<style>body{font-family:system-ui,-apple-system,sans-serif;padding:1.5rem;color:#111;line-height:1.6;}</style>"
            f"</head><body>{sanitize_html(text)}</body></html>"
        )
        return boilerplate

    # Markdown format
    match = _FENCED_MD_RE.search(text)
    if match:
        return match.group(1).strip()
    return text
