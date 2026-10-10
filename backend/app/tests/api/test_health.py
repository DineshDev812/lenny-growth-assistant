import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import set_test_llm_provider
from app.llm.fake import FakeLLMProvider
from app.services import health as health_service


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["provider"]
    assert body["model"]
    assert body["provider_status"] == "ok"
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_health_database_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail_ping(_db: AsyncSession) -> None:
        raise OperationalError("SELECT 1", {}, Exception("could not connect"))

    monkeypatch.setattr(health_service, "ping", fail_ping)

    response = client.get("/health")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "db_down"
    assert error["message"]
    assert error["request_id"]
    assert response.headers["X-Request-ID"] == error["request_id"]


def test_health_llm_down_keeps_200(client: TestClient) -> None:
    set_test_llm_provider(FakeLLMProvider(health_status="unavailable"))
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["provider_status"] == "unavailable"
    finally:
        set_test_llm_provider(None)


def test_meta_endpoint(client: TestClient) -> None:
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"]
    assert body["provider"]
    assert body["model"]
    assert body["provider_status"] in ("ok", "unconfigured", "unavailable", "unknown")


def test_request_id_echoed(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "fixed-id-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "fixed-id-123"
