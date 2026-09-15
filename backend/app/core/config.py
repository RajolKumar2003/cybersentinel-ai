"""
Central application configuration.

All values are read from environment variables (see .env.example).
No secrets, credentials, or API keys are hard-coded anywhere in this file
or anywhere else in the codebase — that is a hard project rule enforced
by code review / CI secret-scanning conventions documented in SECURITY.md.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App metadata -----------------------------------------------------
    app_name: str = "CyberSentinel AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True

    # --- Database -----------------------------------------------------------
    # Defaults to a local SQLite file so the project runs with zero external
    # services. Set DATABASE_URL to a postgresql+psycopg://... URL to use
    # PostgreSQL instead (SQLAlchemy models are database-agnostic).
    database_url: str = "sqlite:///./cybersentinel.db"

    # --- Vector store ---------------------------------------------------
    vector_store_path: str = "./data/vector_store"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- LLM provider -----------------------------------------------------
    # "mock" is the default: a free, offline, deterministic rule-based
    # provider used for all agent reasoning so the project runs with zero
    # API keys and zero cost. Set llm_provider="openai_compatible" and
    # supply LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME to point at a real
    # hosted model instead. There is no "unlimited free" hosted LLM API —
    # the mock provider is the genuinely free/unlimited option.
    llm_provider: Literal["mock", "openai_compatible"] = "mock"
    llm_api_key: str | None = Field(default=None, repr=False)
    llm_base_url: str | None = None
    llm_model_name: str = "mock-security-analyst-v1"

    # --- Security -----------------------------------------------------------
    secret_key: str = Field(default="change-me-in-.env", repr=False)
    cors_allow_origins: list[str] = ["http://localhost:8501", "http://localhost:3000"]
    rate_limit_per_minute: int = 60

    # --- Anomaly detection --------------------------------------------------
    anomaly_model_dir: str = "./ml/artifacts"
    anomaly_contamination: float = 0.05  # expected fraction of anomalies, demo default


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (safe to call repeatedly)."""
    return Settings()
