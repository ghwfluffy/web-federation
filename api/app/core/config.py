from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

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

    app_name: str = "Central Auth"
    app_env: str = "development"
    app_version: str = __version__
    app_base_path: str = "/auth"
    api_v1_prefix: str = "/api/v1"
    public_url: str = "http://localhost:8090"
    postgres_user: str = "ghw"
    postgres_password: str = "supersecure"
    postgres_db: str = "auth_site"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    session_key: str | None = None
    session_key_source: Literal["env", "default", "generated"] = "env"
    session_cookie_name: str = "auth_session"
    session_duration_minutes: int = 60
    auth_max_failed_attempts: int = 5
    auth_lockout_minutes: int = 15
    goals_base_url: str = "/goals"
    money_planner_base_url: str = "/money-planner"
    backup_dir: str = str(ROOT_DIR / "backups")
    backup_script_path: str = str(ROOT_DIR / "db" / "create_backup.sh")
    cors_origins: list[str] = [
        "http://127.0.0.1:8091",
        "http://localhost:8091",
        "http://127.0.0.1:8090",
        "http://localhost:8090",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

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
