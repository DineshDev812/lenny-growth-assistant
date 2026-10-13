from __future__ import annotations

import pytest

from app.agent.router import classify_intent, classify_route, is_smalltalk


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hi", True),
        ("hello", True),
        ("hey", True),
        ("hey there", True),
        ("howdy", True),
        ("sup", True),
        ("yo", True),
        ("good morning", True),
        ("good afternoon", True),
        ("good evening", True),
        ("greetings", True),
        ("thanks", True),
        ("thank you", True),
        ("thx", True),
        ("ty", True),
        ("many thanks", True),
        ("appreciate it", True),
        ("thank you so much", True),
        ("thanks a lot!", True),
        ("who are you", True),
        ("what can you do", True),
        ("what are you?", True),
        ("help", True),
        ("who made you", True),
        ("who created you", True),
        ("what is your name", True),
        ("how can you help?", True),
        # Non-smalltalk queries
        ("What is product-market fit?", False),
        ("How to make chocolate cookies?", False),
        ("Write an essay on retention", False),
        ("Who is Brian Chesky?", False),
        ("Tell me about Lenny's background", False),
    ],
)
def test_is_smalltalk(text: str, expected: bool) -> None:
    assert is_smalltalk(text) is expected


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
        ("Tell me a cookie recipe", "general", "general"),
    ],
)
def test_classify_intent(
    content: str,
    explicit_intent: str | None,
    expected: str,
) -> None:
    assert classify_intent(content, explicit_intent) == expected


@pytest.mark.parametrize(
    ("content", "explicit_intent", "expected_route"),
    [
        # 1-7: Smalltalk / greetings / pleasantries / help
        ("hi", None, "smalltalk"),
        ("Hello!", None, "smalltalk"),
        ("hey there", None, "smalltalk"),
        ("good morning", None, "smalltalk"),
        ("thanks", None, "smalltalk"),
        ("thank you so much!", None, "smalltalk"),
        ("who are you", None, "smalltalk"),
        ("what can you do?", None, "smalltalk"),
        ("help", None, "smalltalk"),
        # 8-15: General / everyday / out-of-domain questions
        ("What is the recipe for chocolate chip cookies?", None, "general"),
        ("Who won the NBA finals in 2023?", None, "general"),
        ("How do I set up a Kubernetes ingress controller in AWS?", None, "general"),
        ("What is 47 * 89?", None, "general"),
        ("Write a Python function to reverse a doubly linked list.", None, "general"),
        ("What is the capital of Australia?", None, "general"),
        ("How to fix a leaking bathroom sink pipe?", None, "general"),
        ("Explain quantum computing in simple terms.", None, "general"),
        # 16-27: Grounded domain questions (product, growth, podcast terms)
        ("How do you measure product-market fit according to Lenny's guests?", None, "grounded"),
        ("What about B2B?", None, "grounded"),
        ("What is Lenny's framework for customer retention?", None, "grounded"),
        ("How did Figma find its first 1,000 users?", None, "grounded"),
        ("What did Brian Chesky say about design-led companies?", None, "grounded"),
        ("How do you calculate LTV to CAC ratio?", None, "grounded"),
        ("What are the best onboarding activation metrics for SaaS?", None, "grounded"),
        ("How does Patrick Campbell think about pricing strategy?", None, "grounded"),
        ("What did Elena Verna say about B2B product-led growth?", None, "grounded"),
        ("How to hire an early-stage head of growth?", None, "grounded"),
        ("What is a viral growth loop and how do you design one?", None, "grounded"),
        ("How do network effects create defensibility for marketplaces?", None, "grounded"),
        # 28-34: Essay route
        ("Write a Ship 30 for 30 essay on retention and churn.", None, "essay"),
        ("Draft an atomic essay about finding product market fit.", None, "essay"),
        ("Write an article on user activation funnels.", None, "essay"),
        ("Create a newsletter edition summarizing growth tactics.", None, "essay"),
        ("Draft a post on why Net Revenue Retention matters.", None, "essay"),
        ("Can you write a deep dive guide on startup pricing?", None, "essay"),
        ("Ship 30 essay on product management leadership.", None, "essay"),
        # 35-40: Artifact route
        ("Build an interactive calculator in HTML for unit economics.", None, "artifact"),
        ("Generate an HTML widget showing customer churn rate.", None, "artifact"),
        ("Create a landing page mockup for a growth tool in HTML.", None, "artifact"),
        ("Build an interactive UI component with HTML and CSS.", None, "artifact"),
        ("Make an HTML one-pager about user activation.", None, "artifact"),
        ("Generate a calculator widget for CAC payback period.", None, "artifact"),
        # 41-48: Explicit intent overrides
        ("What is the recipe for cookies?", "general", "general"),
        ("How do you measure PMF?", "general", "general"),
        ("What is PMF?", "qa", "grounded"),
        ("What is retention?", "essay", "essay"),
        ("What is activation?", "artifact", "artifact"),
        ("Hello Lenny", "general", "general"),
        ("Tell me about sports", "qa", "grounded"),
        ("Write an essay on pricing", "artifact", "artifact"),
    ],
)
def test_classify_route(
    content: str,
    explicit_intent: str | None,
    expected_route: str,
) -> None:
    assert classify_route(content, explicit_intent) == expected_route


@pytest.mark.parametrize(
    ("content", "prev_route", "expected_route"),
    [
        # Short non-domain queries (<= 12 words) follow grounded route
        ("Can you elaborate on that?", "grounded", "grounded"),
        ("What does that mean in practice?", "grounded", "grounded"),
        ("Are there any examples?", "grounded", "grounded"),
        # Starting with conversational phrases
        ("What about for enterprise B2B?", "grounded", "grounded"),
        ("How about early stage startups?", "grounded", "grounded"),
        ("Did they test that with consumer apps?", "grounded", "grounded"),
        ("And how often should we review this?", "grounded", "grounded"),
        ("How often should founders do this?", "grounded", "grounded"),
        # Long query (> 12 words) starting with follow-up phrase
        (
            "What about the case where an enterprise team with fifty engineers is migrating to a brand new service architecture?",
            "grounded",
            "grounded",
        ),
        # Long non-domain query (> 12 words) NOT starting with follow-up phrase routes to general even if prev was grounded
        (
            "Explain the historical background of the Treaty of Versailles signed in nineteen nineteen between European nations in detail.",
            "grounded",
            "general",
        ),
        # Smalltalk takes precedence over grounded follow-up
        ("thanks", "grounded", "smalltalk"),
        ("thank you so much", "grounded", "smalltalk"),
        ("hello", "grounded", "smalltalk"),
        # Explicit intent overrides
        ("What about that?", "grounded", "grounded"),
        # When prev_route is not grounded, non-domain short queries route to general
        ("Can you elaborate on that?", None, "general"),
        ("Can you elaborate on that?", "general", "general"),
        ("Did they test that with consumer apps?", None, "general"),
        ("Did they test that with consumer apps?", "general", "general"),
    ],
)
def test_classify_route_conversational_follow_up(
    content: str,
    prev_route: str | None,
    expected_route: str,
) -> None:
    assert classify_route(content, prev_route=prev_route) == expected_route

