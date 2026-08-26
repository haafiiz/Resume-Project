"""
Application configuration.

All configuration is sourced from environment variables (optionally loaded
from a local .env file). Nothing here should ever contain real secrets -
see .env.example at the repository root for the documented list of
variables a developer needs to set.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Resume Tailoring Platform"
    app_env: str = "development"  # development | test | production
    debug: bool = True

    # --- API ---
    api_v1_prefix: str = "/api/v1"

    # --- CORS ---
    # Comma-separated list of allowed origins for the frontend dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    database_url: str = "sqlite:///./storage/app.db"

    # --- AI / Ollama (configuration only - not used until a later sprint) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # --- File uploads (configuration only - not used until a later sprint) ---
    max_upload_size_mb: int = 10
    allowed_upload_extensions: str = ".pdf,.docx"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_upload_extension_list(self) -> List[str]:
        return [ext.strip() for ext in self.allowed_upload_extensions.split(",") if ext.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using lru_cache means the environment is only read once per process,
    while still allowing tests to override settings via dependency
    overrides if ever needed.
    """
    return Settings()
