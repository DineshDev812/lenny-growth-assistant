from __future__ import annotations

from app.services.query_builder import (
    build_retrieval_query,
    extract_salient_terms,
    is_follow_up,
)


def test_is_follow_up_short_query() -> None:
    assert is_follow_up("What about B2B?") is True
    assert is_follow_up("Why?") is True
    assert is_follow_up("Tell me more.") is True


def test_is_follow_up_pronouns() -> None:
    assert is_follow_up("How does it work in large enterprise companies?") is True
    assert is_follow_up("Did they test that with real users?") is True
    assert is_follow_up("What was her recommendation for pricing tiers?") is True


def test_is_follow_up_starts_with_conjunction() -> None:
    assert is_follow_up("And what did Brian say about founder mode?") is True
    assert is_follow_up("How about consumer subscription models?") is True


def test_is_not_follow_up_self_contained() -> None:
    assert is_follow_up("How to calculate customer lifetime value in enterprise SaaS?") is False
    assert is_follow_up("Explain the difference between product market fit and go to market.") is False


def test_extract_salient_terms() -> None:
    prev = "What did Brian Chesky say about founder mode and design at Airbnb?"
    terms = extract_salient_terms(prev, max_terms=6)
    assert "brian" in terms
    assert "chesky" in terms
    assert "founder" in terms
    assert "mode" in terms
    assert "design" in terms
    assert "airbnb" in terms
    # Stopwords omitted
    assert "what" not in terms
    assert "did" not in terms
    assert "about" not in terms
    assert "and" not in terms


def test_build_retrieval_query_enriches_follow_up() -> None:
    prev = "How did Figma achieve rapid PLG adoption and virality?"
    curr = "What about pricing?"

    query = build_retrieval_query(curr, previous_user_message=prev)
    assert query.startswith("What about pricing?")
    assert "figma" in query
    assert "achieve" in query
    assert "rapid" in query
    assert "plg" in query


def test_build_retrieval_query_leaves_standalone_query_intact() -> None:
    prev = "How did Figma achieve rapid PLG adoption?"
    curr = "Explain the retention lifecycle framework described by Casey Winters."

    query = build_retrieval_query(curr, previous_user_message=prev)
    assert query == curr


def test_build_retrieval_query_caps_length() -> None:
    long_prev = "word " * 100
    curr = "What about it?"
    query = build_retrieval_query(curr, previous_user_message=long_prev, max_chars=100)
    assert len(query) <= 100
