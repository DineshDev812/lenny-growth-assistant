from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class FakeLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        canned_response: str = "This is a deterministic fake assistant response grounded in [S1].",
        tokens: list[str] | None = None,
        health_status: str = "ok",
        provider_name: str = "fake",
        model_name: str = "fake-model",
    ) -> None:
        self._canned_response = canned_response
        self._tokens = tokens or ["This ", "is ", "a ", "fake ", "stream."]
        self._health_status = health_status
        self._provider = provider_name
        self._model = model_name

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return LLMResponse(
            content=self._canned_response,
            provider=self.provider_name,
            model=self.model_name,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        for token in self._tokens:
            yield token

    async def health(self) -> str:
        return self._health_status
