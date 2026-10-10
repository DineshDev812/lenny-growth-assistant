from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.core.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnconfiguredError,
)
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-5",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key.strip() if api_key else ""
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_configured(self) -> None:
        if not self._api_key:
            raise ProviderUnconfiguredError(
                "Anthropic API key is not configured. Add ANTHROPIC_API_KEY to your .env file."
            )

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self._ensure_configured()

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key, timeout=self._timeout)
            claude_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            kwargs: dict[str, object] = {
                "model": self._model,
                "messages": claude_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await client.messages.create(**kwargs)
            text_blocks = [
                block.text for block in response.content if getattr(block, "type", "") == "text"
            ]
            content = "".join(text_blocks)
            return LLMResponse(content=content, provider=self.provider_name, model=self.model_name)

        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name:
                raise ProviderTimeoutError(f"Anthropic request timed out: {exc}") from exc
            if "Connection" in err_name:
                raise ProviderUnavailableError(f"Could not connect to Anthropic API: {exc}") from exc
            if "Authentication" in err_name:
                raise ProviderUnconfiguredError(f"Anthropic authentication failed: {exc}") from exc
            logger.exception("Anthropic error: %s", exc)
            raise ProviderUnavailableError(f"Anthropic API error: {exc}") from exc

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        self._ensure_configured()

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key, timeout=self._timeout)
            claude_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            kwargs: dict[str, object] = {
                "model": self._model,
                "messages": claude_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as exc:
            err_name = type(exc).__name__
            if "Timeout" in err_name:
                raise ProviderTimeoutError(f"Anthropic stream timed out: {exc}") from exc
            if "Connection" in err_name:
                raise ProviderUnavailableError(f"Could not connect to Anthropic API: {exc}") from exc
            if "Authentication" in err_name:
                raise ProviderUnconfiguredError(f"Anthropic authentication failed: {exc}") from exc
            logger.exception("Anthropic stream error: %s", exc)
            raise ProviderUnavailableError(f"Anthropic streaming error: {exc}") from exc

    async def health(self) -> str:
        if not self._api_key:
            return "unconfigured"
        return "ok"
