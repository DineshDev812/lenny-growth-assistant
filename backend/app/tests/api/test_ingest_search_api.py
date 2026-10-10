from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api import ingest as ingest_api
from app.core.config import Settings
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def api(db_factory, make_runner, transcripts_dir: Path) -> AsyncIterator[AsyncClient]:
    async def override_get_db():  # type: ignore[no-untyped-def]
        async with db_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.state.ingest_runner = make_runner(transcripts_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


async def test_status_is_idle_before_any_run(api: AsyncClient) -> None:
    body = (await api.get("/api/ingest/status")).json()
    assert body["state"] == "idle"
    assert body["total_episodes"] == 0


async def test_post_ingest_wait_returns_final_counts(api: AsyncClient) -> None:
    response = await api.post("/api/ingest", params={"wait": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "completed"
    assert body["episodes_ingested"] == 5
    assert body["episodes_skipped"] == 0
    assert body["chunks_created"] >= 5
    assert body["total_episodes"] == 5

    again = (await api.post("/api/ingest", params={"wait": "true"})).json()
    assert again["episodes_ingested"] == 0
    assert again["episodes_skipped"] == 5

    status = (await api.get("/api/ingest/status")).json()
    assert status["state"] == "completed"
    assert status["total_chunks"] == body["total_chunks"]


async def test_post_ingest_without_wait_is_accepted(api: AsyncClient) -> None:
    response = await api.post("/api/ingest")
    assert response.status_code == 202
    assert response.json()["trigger"] == "manual"
    await app.state.ingest_runner.wait()
    assert (await api.get("/api/ingest/status")).json()["state"] == "completed"


async def test_ingest_token_is_enforced_when_configured(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ingest_api, "get_settings", lambda: Settings(ingest_token="s3cret"))
    denied = await api.post("/api/ingest")
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "unauthorized"
    wrong = await api.post("/api/ingest", headers={"X-Ingest-Token": "nope"})
    assert wrong.status_code == 401
    ok = await api.post("/api/ingest", headers={"X-Ingest-Token": "s3cret"}, params={"wait": "true"})
    assert ok.status_code == 200


async def test_search_returns_ranked_chunks_with_links(api: AsyncClient) -> None:
    await api.post("/api/ingest", params={"wait": "true"})
    response = await api.get("/api/search", params={"q": "how do I improve activation", "k": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["results"]) >= 1
    top = body["results"][0]
    assert top["episode_slug"] == "activation-expert"
    assert top["youtube_deep_link"].endswith(f"&t={top['start_seconds']}")
    assert set(top) >= {
        "episode_title", "guest", "publish_date", "youtube_url", "youtube_deep_link",
        "start_seconds", "start_timestamp", "score", "text",
    }


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "   "}, {"q": "zxqvbnmlkjh"}, {"q": '"'}, {"q": "&|!"}])
async def test_search_empty_and_nonsense_return_empty_list_not_error(api: AsyncClient, params: dict) -> None:
    await api.post("/api/ingest", params={"wait": "true"})
    response = await api.get("/api/search", params=params)
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["count"] == 0


async def test_search_with_empty_database_returns_empty_list(api: AsyncClient) -> None:
    response = await api.get("/api/search", params={"q": "activation"})
    assert response.status_code == 200
    assert response.json()["results"] == []


async def test_search_validates_k(api: AsyncClient) -> None:
    response = await api.get("/api/search", params={"q": "activation", "k": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_post_ingest_conflict_when_already_running(api: AsyncClient) -> None:
    app.state.ingest_runner._state.state = "running"
    try:
        response = await api.post("/api/ingest")
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "ingest_in_progress"
        assert body["error"]["request_id"]
    finally:
        app.state.ingest_runner._state.state = "idle"


async def test_search_by_guest_and_keywords(api: AsyncClient) -> None:
    await api.post("/api/ingest", params={"wait": "true"})
    # Guest name search
    by_guest = await api.get("/api/search", params={"q": "Ada Activation"})
    assert by_guest.status_code == 200
    assert len(by_guest.json()["results"]) >= 1
    assert by_guest.json()["results"][0]["episode_slug"] == "activation-expert"

    # Keywords search
    by_kw = await api.get("/api/search", params={"q": "aha moment"})
    assert by_kw.status_code == 200
    assert len(by_kw.json()["results"]) >= 1
    assert by_kw.json()["results"][0]["episode_slug"] == "activation-expert"
