from __future__ import annotations

from collections.abc import AsyncIterator
from fastapi.testclient import TestClient

from app.core.exceptions import ProviderTimeoutError, ProviderUnavailableError
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from app.llm.factory import set_test_llm_provider


class FailingLLMProvider(BaseLLMProvider):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    @property
    def provider_name(self) -> str:
        return "failing-provider"

    @property
    def model_name(self) -> str:
        return "failing-model"

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        raise self._exc

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        raise self._exc
        yield ""  # Make it an async generator

    async def health(self) -> str:
        return "unavailable"


def test_sync_timeout_maps_to_504(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    set_test_llm_provider(FailingLLMProvider(ProviderTimeoutError("Internal socket timeout")))
    try:
        res = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "What is activation?"},
        )
        assert res.status_code == 504
        error = res.json()["error"]
        assert error["code"] == "model_timeout"
        assert "socket" not in error["message"].lower()  # Raw exception not leaked
        assert error["request_id"]
    finally:
        set_test_llm_provider(None)


def test_sync_unavailable_maps_to_503(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    set_test_llm_provider(FailingLLMProvider(ProviderUnavailableError("Connection refused 127.0.0.1:11434")))
    try:
        res = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "What is activation?"},
        )
        assert res.status_code == 503
        error = res.json()["error"]
        assert error["code"] == "model_unavailable"
        assert "127.0.0.1" not in error["message"]  # Server details not leaked
        assert error["request_id"]
    finally:
        set_test_llm_provider(None)


def test_stream_error_sse_events(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    set_test_llm_provider(FailingLLMProvider(ProviderTimeoutError("Deadline exceeded")))
    try:
        res = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "What is activation?"},
            headers={"Accept": "text/event-stream"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        text = res.text
        assert "event: error" in text
        assert '"code": "model_timeout"' in text
        assert '"retryable": true' in text
        assert "Deadline exceeded" not in text  # User-safe message
    finally:
        set_test_llm_provider(None)
