"""Validated environment configuration, loaded once on first use."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseSettings):
    """Configure the HTTP UI without requiring backend service credentials."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        alias_generator=str.upper,
        populate_by_name=True,
        hide_input_in_errors=True,
        frozen=True,
    )

    api_base_url: str = Field(default="http://127.0.0.1:8000", min_length=1)
    api_timeout_seconds: float = Field(default=180, gt=0, allow_inf_nan=False)


class Settings(ClientSettings):
    """Read and validate all backend environment configuration."""

    external_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    query_lock_timeout_seconds: float = Field(default=180, gt=0, allow_inf_nan=False)

    gemini_api_key: SecretStr
    gemini_model: str = Field(default="gemini-2.5-flash-lite", min_length=1)
    qdrant_url: str = Field(min_length=1)
    qdrant_api_key: SecretStr | None = None
    neo4j_uri: str = Field(min_length=1)
    neo4j_username: str = Field(min_length=1)
    neo4j_password: SecretStr
    kanoon_token: SecretStr

    top_k: int = Field(default=30, ge=1)
    rerank_k: int = Field(default=5, ge=1)
    judgment_k: int = Field(default=5, ge=1)
    pass_threshold: float = Field(default=80, ge=0, le=100)
    max_attempts: int = Field(default=3, ge=1)
    log_level: str = "INFO"

    @field_validator("gemini_api_key", "neo4j_password", "kanoon_token")
    @classmethod
    def nonempty_secret(cls, value: SecretStr) -> SecretStr:
        """Reject blank credentials without including their values in errors."""
        if not value.get_secret_value().strip():
            raise ValueError("Required credential must not be blank")
        return value

    @field_validator("gemini_model", "qdrant_url", "neo4j_uri", "neo4j_username")
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        """Reject whitespace-only service configuration."""
        if not value.strip():
            raise ValueError("Required setting must not be blank")
        return value

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def optional_key(cls, value: object) -> object:
        """Allow an empty optional key for unauthenticated local Qdrant."""
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        """Accept only standard Python logging levels."""
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Invalid logging level")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings; restart the app after env changes."""
    return Settings()


@lru_cache(maxsize=1)
def get_client_settings() -> ClientSettings:
    """Load UI connection settings independently of backend credentials."""
    return ClientSettings()


class EvaluationSettings(ClientSettings):
    """Configure dataset tooling independently of Neo4j and Indian Kanoon."""

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None
    external_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    pass_threshold: float = Field(default=80, ge=0, le=100)
