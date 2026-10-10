from __future__ import annotations

from typing import Optional

from app.core.config import Settings, get_settings
from app.llm.anthropic import AnthropicProvider
from app.llm.base import BaseLLMProvider
from app.llm.ollama import OllamaProvider

_test_provider: Optional[BaseLLMProvider] = None


def set_test_llm_provider(provider: Optional[BaseLLMProvider]) -> None:
    """Override the global provider for deterministic tests."""
    global _test_provider
    _test_provider = provider


def get_llm_provider(settings: Settings | None = None) -> BaseLLMProvider:
    if _test_provider is not None:
        return _test_provider

    cfg = settings or get_settings()
    provider_type = (cfg.model_provider or "ollama").lower().strip()

    if provider_type == "anthropic":
        return AnthropicProvider(
            api_key=cfg.anthropic_api_key,
            model=cfg.anthropic_model,
            timeout=cfg.llm_timeout,
        )

    return OllamaProvider(
        base_url=cfg.ollama_base_url,
        model=cfg.ollama_model,
        timeout=cfg.llm_timeout,
    )
