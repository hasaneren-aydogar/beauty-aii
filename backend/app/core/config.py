from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Beauty AI"
    environment: Literal["development", "production", "test"] = "development"

    database_url: str = "postgresql+psycopg://beauty:beauty@localhost:5432/beauty"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    kiosk_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    storage_dir: str = "./storage"
    image_ttl_minutes: int = 30
    cleanup_interval_seconds: int = 60
    max_upload_mb: int = 8
    max_image_side: int = 1280

    rate_limit_default: str = "120/minute"
    rate_limit_try: str = "6/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_rag: str = "30/minute"

    ai_backend: Literal["mock", "hairfast"] = "mock"
    ai_fallback_to_mock: bool = True
    hairfast_repo_path: str = "../ai-models/HairFastGAN"

    embedding_backend: Literal["hash", "sentence_transformers"] = "hash"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384

    llm_backend: Literal["extractive", "openai_compat"] = "extractive"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.1:8b"
    rag_top_k: int = 4
    rag_max_distance: float = 0.8

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
