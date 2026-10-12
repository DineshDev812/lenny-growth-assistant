from __future__ import annotations

import pytest

from app.services.sanitizer import (
    FALLBACK_SAFE_MESSAGE,
    extract_artifact_content,
    sanitize_html,
)


def test_xss_corpus_neutralized() -> None:
    corpus = [
        ("<script>alert(1)</script>", ["<script", "alert(1)"]),
        ('<img src="x" onerror="alert(1)">', ["onerror", "alert(1)"]),
        ('<a href="javascript:alert(1)">Click me</a>', ["javascript:"]),
        ('<div style="background:url(javascript:alert(1))">Box</div>', ["style=", "javascript:"]),
        ('<iframe src="https://evil.com"></iframe>', ["<iframe", "https://evil.com"]),
        ('<form action="https://evil.com"><input type="text"><button>Submit</button></form>', ["<form", "<input", "<button"]),
        ('<svg onload="alert(1)"></svg>', ["<svg", "onload"]),
        ('<math><mi xlink:href="javascript:alert(1)"></mi></math>', ["<math", "javascript:"]),
    ]

    for payload, dangerous_substrings in corpus:
        cleaned = sanitize_html(payload)
        for sub in dangerous_substrings:
            assert sub.lower() not in cleaned.lower(), f"Failed to neutralize {sub} in payload {payload}: result was {cleaned}"


def test_sanitize_html_strips_style_and_button_tags() -> None:
    html = """
    <div>
        <style>body { background: red; }</style>
        <h2>Safe Title</h2>
        <button onclick="doAction()">Click</button>
        <p>Legitimate text</p>
    </div>
    """
    cleaned = sanitize_html(html)
    assert "<style" not in cleaned
    assert "background: red" not in cleaned
    assert "<button" not in cleaned
    assert "onclick" not in cleaned
    assert "<h2>Safe Title</h2>" in cleaned
    assert "<p>Legitimate text</p>" in cleaned


def test_sanitize_html_strips_data_urls() -> None:
    html = '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAE" alt="test">'
    cleaned = sanitize_html(html)
    assert "data:" not in cleaned
    assert "base64" not in cleaned


def test_sanitize_html_adds_noopener_noreferrer() -> None:
    html = '<a href="https://lennysnewsletter.com">Lenny\'s Newsletter</a>'
    cleaned = sanitize_html(html)
    assert 'href="https://lennysnewsletter.com"' in cleaned
    assert 'rel="noopener noreferrer"' in cleaned


def test_sanitize_html_fail_closed_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.sanitizer as san_module

    def buggy_clean(*args: object, **kwargs: object) -> str:
        raise RuntimeError("Internal C parser memory corruption")

    monkeypatch.setattr(san_module.nh3, "clean", buggy_clean)
    result = sanitize_html("<div>Some HTML</div>")
    assert result == FALLBACK_SAFE_MESSAGE


def test_extract_artifact_content_fenced_html() -> None:
    model_response = """
    Here is an interactive retention framework:
    ```html
    <div class="card">
        <h3>Retention Ladder</h3>
        <p>Step 1: Setup habit loop.</p>
    </div>
    ```
    I hope this helps you build strong retention!
    """
    extracted = extract_artifact_content(model_response, "html")
    assert "Here is an interactive" not in extracted
    assert "I hope this helps" not in extracted
    assert "Retention Ladder" in extracted
    assert '<div class="card">' in extracted


def test_extract_artifact_content_bare_html_boilerplate() -> None:
    model_response = "<h3>Unfenced Heading</h3><p>Direct paragraph.</p>"
    extracted = extract_artifact_content(model_response, "html")
    assert "<!DOCTYPE html>" in extracted
    assert "<html>" in extracted
    assert "<h3>Unfenced Heading</h3>" in extracted
    assert "<p>Direct paragraph.</p>" in extracted


def test_extract_artifact_content_fenced_markdown() -> None:
    model_response = """
    Below is your Ship 30 for 30 essay:
    ```markdown
    # How to Build a Growth Engine

    Growth is not an accident. It is a compounding flywheel.

    ## 1. The Core Loop
    Activation leads to retention.
    ```
    Good luck implementing this!
    """
    extracted = extract_artifact_content(model_response, "markdown")
    assert "Below is your Ship 30" not in extracted
    assert "Good luck implementing" not in extracted
    assert "# How to Build a Growth Engine" in extracted
    assert "## 1. The Core Loop" in extracted
