from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Atelier"
    jwt_secret: str = "dev-only-change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    database_url: str = "postgresql+psycopg://fashion:fashion@127.0.0.1:5432/fashion"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    public_app_url: str = "http://localhost:5173"
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    embedding_provider: str = "local"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    shipping_flat: Decimal = Decimal("8.00")
    free_shipping_over: Decimal = Decimal("150.00")
    rate_limit_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key.strip())

    @property
    def dev_reset_tokens(self) -> bool:
        return self.app_env in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
