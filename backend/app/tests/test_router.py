from __future__ import annotations

import pytest

from app.agent.router import classify_intent


@pytest.mark.parametrize(
    ("content", "explicit_intent", "expected"),
    [
        # Clear Q&A queries
        ("What is product-led growth?", None, "qa"),
        ("How did Figma find its first 1,000 users?", None, "qa"),
        ("Can you explain Lenny's framework for retention?", None, "qa"),
        ("What metrics matter most for early-stage B2B startups?", None, "qa"),
        ("Who was the guest that talked about onboarding funnels?", None, "qa"),
        ("Tell me about pricing tiers according to Patrick Campbell.", None, "qa"),
        ("How to hire the first product manager?", None, "qa"),
        ("What did Brian Chesky say about design-led companies?", None, "qa"),
        # Clear Essay queries
        ("Write an essay on consumer growth loops.", None, "essay"),
        ("Please draft a Ship 30 style essay about retention.", None, "essay"),
        ("Create an atomic essay on finding product market fit.", None, "essay"),
        ("Write an article comparing sales-led and product-led motions.", None, "essay"),
        ("Draft a post on why Net Revenue Retention is the holy grail.", None, "essay"),
        ("Write a deep dive guide on marketplace liquidity.", None, "essay"),
        ("Create a newsletter edition summarizing Lenny's best growth advice.", None, "essay"),
        ("Can you do a Ship30 breakdown of viral loops?", None, "essay"),
        # Clear Artifact queries
        ("Build an interactive calculator in HTML for churn rate.", None, "artifact"),
        ("Generate an HTML widget showing the retention curve.", None, "artifact"),
        ("Create a landing page mockup for a growth tool in html.", None, "artifact"),
        ("Give me a UI component with HTML and CSS for pricing.", None, "artifact"),
        ("Create a code artifact for a funnel visualizer.", None, "artifact"),
        ("Can you provide a CSS snippet for a dashboard card?", None, "artifact"),
        ("Generate a calculator for customer lifetime value.", None, "artifact"),
        # Edge cases: Case sensitivity, whitespace, punctuation
        ("   WRITE AN ESSAY ON PM CAREERS   ", None, "essay"),
        ("??? Write a post about churn and activation !!!", None, "essay"),
        ("HTML DASHBOARD WIDGET", None, "artifact"),
        ("", None, "qa"),
        ("   ", None, "qa"),
        # Explicit intent overrides content classification
        ("Explain PLG motions in detail.", "essay", "essay"),
        ("Write an essay on pricing models.", "qa", "qa"),
        ("Build an HTML widget for funnels.", "qa", "qa"),
        ("What is retention?", "artifact", "artifact"),
    ],
)
def test_classify_intent(
    content: str,
    explicit_intent: str | None,
    expected: str,
) -> None:
    assert classify_intent(content, explicit_intent) == expected
