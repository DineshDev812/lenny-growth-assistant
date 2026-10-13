from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import ProviderTimeoutError, ProviderUnavailableError
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str = "http://host.docker.internal:11434",
        model: str = "qwen2.5:3b",
        timeout: float = 180.0,
        num_ctx: int = 3072,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._num_ctx = num_ctx

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_payload(
        self,
        messages: list[LLMMessage],
        system_prompt: str | None,
        stream: bool,
        temperature: float,
        max_tokens: int = 1500,
        num_ctx: int | None = None,
    ) -> dict[str, object]:
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            payload_messages.append({"role": msg.role, "content": msg.content})

        ctx = num_ctx if num_ctx is not None else self._num_ctx
        return {
            "model": self._model,
            "messages": payload_messages,
            "stream": stream,
            "keep_alive": "24h",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": ctx,
            },
        }

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        num_ctx: int | None = None,
    ) -> LLMResponse:
        url = f"{self._base_url}/api/chat"
        payload = self._build_payload(
            messages,
            system_prompt,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        )
        timeout = httpx.Timeout(self._timeout, connect=5.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise ProviderUnavailableError(f"Ollama returned HTTP {res.status_code}: {res.text}")
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return LLMResponse(content=content, provider=self.provider_name, model=self.model_name)
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.warning("Ollama connection failed: %s", exc)
            raise ProviderUnavailableError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            logger.warning("Ollama request timed out: %s", exc)
            raise ProviderTimeoutError(f"Ollama request timed out after {self._timeout}s.") from exc

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        num_ctx: int | None = None,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url}/api/chat"
        payload = self._build_payload(
            messages,
            system_prompt,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
        )
        timeout = httpx.Timeout(self._timeout, connect=5.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderUnavailableError(f"Ollama returned HTTP {response.status_code}: {body.decode()}")
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.warning("Ollama stream connection failed: %s", exc)
            raise ProviderUnavailableError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            logger.warning("Ollama stream timed out: %s", exc)
            raise ProviderTimeoutError(f"Ollama request timed out after {self._timeout}s.") from exc

    async def health(self) -> str:
        url = f"{self._base_url}/api/tags"
        timeout = httpx.Timeout(4.0, connect=3.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return "ok"
                return "unavailable"
        except Exception:
            return "unavailable"
