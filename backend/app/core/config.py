from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Lenny Growth Assistant")
    log_level: str = Field(default="INFO")

    database_url: str = Field(
        default="postgresql+asyncpg://lenny:lenny@postgres:5432/lenny"
    )

    secret_key: str = Field(default="change-me-in-local-dev-not-for-production")
    cookie_name: str = Field(default="client_id")
    cookie_secure: bool = Field(default=False)
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:8000")

    model_provider: Literal["ollama", "anthropic"] = Field(default="ollama")
    anthropic_api_key: str | None = Field(default=None)
    anthropic_model: str = Field(default="claude-sonnet-4-5")
    ollama_base_url: str = Field(default="http://host.docker.internal:11434")
    ollama_model: str = Field(default="qwen2.5:3b")
    ingest_token: str | None = Field(default=None)

    transcripts_dir: str = Field(default="/data/transcripts")
    ingest_on_startup: bool = Field(default=True)
    chunk_target_tokens: int = Field(default=450, ge=50)
    chunk_max_tokens: int = Field(default=500, ge=60)
    chunk_overlap_tokens: int = Field(default=60, ge=0)
    retrieval_min_score: float = Field(default=0.03, ge=0.0)
    retrieval_fallback_min_score: float = Field(default=0.12, ge=0.0)
    llm_timeout: float = Field(default=180.0, ge=10.0)

    @field_validator("anthropic_api_key", "ingest_token", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def active_model(self) -> str:
        if self.model_provider == "anthropic":
            return self.anthropic_model
        return self.ollama_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
