from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden with a FENRIX_* env var."""

    model_config = SettingsConfigDict(env_prefix="FENRIX_", env_file=".env", extra="ignore")

    app_name: str = "Fenrix"
    database_url: str = "sqlite:///./fenrix.db"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_minutes: int = 12 * 60
    demo_email: str = "analyst@fenrix.dev"
    demo_password: str = "fenrix-demo"

    # Seed a realistic 50-application portfolio on first start
    seed_demo_data: bool = True

    # Live threat intel (OSV / registries). Off by default so demos work offline.
    live_feeds: bool = False
    http_timeout_seconds: float = 6.0

    # Optional local LLM for migration code. Fenrix works fully without it.
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_enabled: bool = True

    cors_origins: str = "http://localhost:3000"

    # Folder with the exported dashboard (frontend/out). When set, the API serves the UI too.
    static_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
