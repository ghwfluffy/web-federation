from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


def normalize_path_prefix(value: str) -> str:
    trimmed = value.strip()
    if trimmed in {"", "/"}:
        return ""
    with_leading_slash = trimmed if trimmed.startswith("/") else f"/{trimmed}"
    return with_leading_slash.rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str
    app_env: str
    app_version: str
    app_base_path: str
    api_v1_prefix: str
    public_url: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    session_key: str | None
    session_key_source: Literal["env", "default", "generated"] = "env"
    session_cookie_name: str
    session_duration_minutes: int
    auth_max_failed_attempts: int
    auth_lockout_minutes: int
    goals_base_url: str
    money_planner_base_url: str
    backup_dir: str
    backup_script_path: str
    cors_origins: list[str]

    @field_validator("public_url")
    @classmethod
    def public_url_must_be_origin(cls, value: str) -> str:
        parsed = urlsplit(value.rstrip("/"))
        if parsed.path not in {"", "/"}:
            raise ValueError(
                "PUBLIC_URL must be only the scheme and host; put path prefixes in APP_BASE_PATH."
            )
        return value.rstrip("/")

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def normalized_app_base_path(self) -> str:
        return normalize_path_prefix(self.app_base_path)

    @property
    def public_origin(self) -> str:
        return self.public_url.rstrip("/")

    @property
    def public_base_url(self) -> str:
        return f"{self.public_origin}{self.normalized_app_base_path}"

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env not in {"development", "test"}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.session_key is None or settings.session_key == "":
        settings.session_key = token_urlsafe(32)
        settings.session_key_source = "generated"
    elif settings.session_key == "changeme":
        settings.session_key_source = "default"
    else:
        settings.session_key_source = "env"
    if settings.is_production:
        unsafe_values = []
        if settings.session_key_source in {"default", "generated"}:
            unsafe_values.append("SESSION_KEY")
        if settings.postgres_password == "supersecure":
            unsafe_values.append("POSTGRES_PASSWORD")
        if "localhost" in settings.public_url or "127.0.0.1" in settings.public_url:
            unsafe_values.append("PUBLIC_URL")
        if unsafe_values:
            joined_values = ", ".join(unsafe_values)
            raise RuntimeError(f"Unsafe production configuration values: {joined_values}")
    return settings
