from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider, e.g. 'ollama' or 'anthropic'."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the active model, e.g. 'qwen2.5:3b' or 'claude-sonnet-4-5'."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a complete text response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream response tokens as an async generator."""
        ...

    @abstractmethod
    async def health(self) -> str:
        """Check provider status. Returns 'ok' | 'unconfigured' | 'unavailable' | 'unknown'."""
        ...
