from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_timezone: str = "America/Sao_Paulo"
    app_secret_key: str = Field(default="change-me", min_length=8)
    admin_username: str = "admin"
    admin_password: str = "admin"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=480, ge=1)

    database_url: str = "postgresql+asyncpg://emailext:emailext_dev_123@localhost:5433/emailext"

    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/0"
    celery_result_backend: str = "redis://localhost:6380/1"

    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str | None = None
    imap_password: str | None = None

    wp_default_status: Literal["publish", "draft", "pending"] = "draft"

    evolution_api_url: AnyHttpUrl | None = None
    evolution_api_key: str | None = None
    evolution_instance: str = "emailext"
    whatsapp_notify_number: str | None = None

    default_publish_delay: int = Field(default=10, ge=0)
    imap_listener_enabled: bool = True
    settings_storage_path: str = "media/settings.json"
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_enabled: bool = True
    authenticated_rate_limit_per_minute: int = Field(default=60, ge=1)
    auth_login_rate_limit_per_minute: int = Field(default=10, ge=1)
    image_max_width: int = Field(default=1920, ge=1)
    image_convert_to_webp: bool = False
    image_webp_quality: int = Field(default=82, ge=1, le=100)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json
                return json.loads(stripped)
            return [o.strip() for o in stripped.split(",") if o.strip()]
        return list(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
