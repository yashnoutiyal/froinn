from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Frontech Innovations Logistics Platform"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str
    redis_url: str
    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    bootstrap_super_admin_name: str | None = None
    bootstrap_super_admin_email: str | None = None
    bootstrap_super_admin_password: str | None = None
    cors_origins: list[str] = []
    log_level: str = "INFO"
    object_storage_endpoint_url: str | None = None
    object_storage_bucket: str | None = None
    object_storage_region: str | None = None
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: bool | str) -> bool | str:
        """Accept common deployment values such as `release` and `production`."""
        if isinstance(value, str) and value.lower() in {"release", "production", "staging"}:
            return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
