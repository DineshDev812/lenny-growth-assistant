import pytest

from app.services.retrieval import RetrievalService, build_deep_link, extract_terms


@pytest.fixture
async def retrieval(ingested, db_factory):  # type: ignore[no-untyped-def]
    async with db_factory() as db:
        yield RetrievalService(db)


async def test_ranking_puts_the_relevant_episode_first(retrieval) -> None:
    activation = await retrieval.retrieve("how do I improve activation for new users?")
    assert activation and activation[0].episode_slug == "activation-expert"
    retention = await retrieval.retrieve("cohort retention curves and product-market fit")
    assert retention and retention[0].episode_slug == "retention-guru"
    pricing = await retrieval.retrieve("pricing experiment packaging")
    assert pricing and pricing[0].episode_slug == "pricing-wizard"


async def test_results_are_sorted_by_score_and_carry_metadata(retrieval) -> None:
    results = await retrieval.retrieve("activation onboarding retention")
    assert len(results) >= 2
    scores = [item.score for item in results]
    assert scores == sorted(scores, reverse=True)
    top = results[0]
    assert top.episode_title
    assert top.guest
    assert top.publish_date is not None
    assert top.youtube_url and top.youtube_url.startswith("https://www.youtube.com/watch?v=")
    assert top.text
    assert 0 < top.score < 1


async def test_deep_link_and_timestamp(retrieval) -> None:
    results = await retrieval.retrieve("activation aha moment onboarding")
    top = results[0]
    assert top.episode_slug == "activation-expert"
    assert top.start_seconds is not None
    assert top.youtube_deep_link == f"{top.youtube_url}&t={top.start_seconds}"
    assert top.start_timestamp and len(top.start_timestamp) == 8


async def test_episode_without_youtube_url_has_no_deep_link(retrieval) -> None:
    results = await retrieval.retrieve("community building moderation")
    assert results and results[0].episode_slug == "no-frontmatter"
    assert results[0].youtube_url is None
    assert results[0].youtube_deep_link is None
    assert results[0].start_timestamp is not None


async def test_or_fallback_when_strict_query_has_no_match(retrieval) -> None:
    # "zebraunicorn" is in no chunk, so the strict AND query matches nothing.
    results = await retrieval.retrieve("activation zebraunicorn")
    assert results
    assert results[0].episode_slug == "activation-expert"


async def test_k_limits_results(retrieval) -> None:
    assert len(await retrieval.retrieve("activation retention pricing hiring community", k=2)) <= 2
    assert await retrieval.retrieve("activation", k=0) == []


@pytest.mark.parametrize(
    "query",
    ["", "   ", "\n\t", "???", "!!!", "'", '"', '"unclosed quote', "- - -", "& | ! ( )", "the and of", "a", "'; DROP TABLE chunks; --", "zxqvbnmlkjh qwrtpsdfg"],
)
async def test_empty_and_nonsense_queries_return_empty_list(retrieval, query: str) -> None:
    assert await retrieval.retrieve(query) == []


async def test_very_long_query_does_not_error(retrieval) -> None:
    assert isinstance(await retrieval.retrieve("activation " * 5000), list)


async def test_none_like_query_does_not_error(retrieval) -> None:
    assert await retrieval.retrieve(None) == []  # type: ignore[arg-type]


async def test_minimum_score_threshold_turns_weak_matches_into_no_results(ingested, db_factory) -> None:
    async with db_factory() as db:
        assert await RetrievalService(db, min_score=0.99).retrieve("activation") == []
        assert await RetrievalService(db, min_score=0.0).retrieve("activation")


async def test_query_injection_is_harmless(retrieval, db_factory) -> None:
    await retrieval.retrieve("'; DELETE FROM chunks; --")
    async with db_factory() as db:
        assert await RetrievalService(db).retrieve("activation")


def test_build_deep_link() -> None:
    assert build_deep_link("https://www.youtube.com/watch?v=abc", 95) == "https://www.youtube.com/watch?v=abc&t=95"
    assert build_deep_link("https://youtu.be/abc", 95) == "https://youtu.be/abc?t=95"
    assert build_deep_link("https://www.youtube.com/watch?v=abc", None) == "https://www.youtube.com/watch?v=abc"
    assert build_deep_link(None, 95) is None


def test_extract_terms_only_returns_safe_tokens() -> None:
    assert extract_terms("How do I fix B2B onboarding? ('; DROP)") == ["how", "do", "fix", "b2b", "onboarding", "drop"]
    assert extract_terms("a ! & |") == []
