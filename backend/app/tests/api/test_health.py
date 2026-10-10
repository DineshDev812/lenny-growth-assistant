import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import health as health_service


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["provider"]
    assert body["model"]
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


def test_request_id_echoed(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "fixed-id-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "fixed-id-123"
