from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    database_url: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    neon_auth_base_url: str | None = None
    import_max_bytes: int = Field(default=2_000_000, ge=1, le=20_000_000)
    import_max_rows: int = Field(default=5_000, ge=1, le=100_000)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @field_validator("neon_auth_base_url")
    @classmethod
    def validate_auth_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("NEON_AUTH_BASE_URL must be an HTTPS URL without credentials or query")
        return value.rstrip("/")

    @model_validator(mode="after")
    def require_production_auth(self) -> "Settings":
        if self.app_env == "production" and not self.neon_auth_base_url:
            raise ValueError("NEON_AUTH_BASE_URL is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
