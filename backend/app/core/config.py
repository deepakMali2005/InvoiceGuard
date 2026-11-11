"""Application configuration loaded from environment variables."""

from pathlib import Path

from functools import lru_cache
from decimal import Decimal
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/app/core/config.py -> project root


class Settings(BaseSettings):
    # Nemotron AI provider (env-driven; never hardcode credentials)
    NEMOTRON_API_ENDPOINT: str = "https://api.nemotron.example.com/v1/chat/completions"
    NEMOTRON_MODEL: str = "nemotron-4"
    NEMOTRON_API_KEY: str = ""
    USE_MOCK_NEMOTRON: bool = True
    NEMOTRON_EXTRACTION_TIMEOUT_SECONDS: int = 30
    NEMOTRON_MAX_RETRIES: int = 2

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://invoiceguard:invoiceguard@localhost:5432/invoiceguard"

    # Local document storage
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 20

    # Reconciliation tolerances (decimal-safe; conservative defaults)
    PRICE_TOLERANCE: str = "0.00"
    QUANTITY_TOLERANCE: str = "0"

    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}

    @property
    def price_tolerance(self) -> Decimal:
        return Decimal(self.PRICE_TOLERANCE)

    @property
    def quantity_tolerance(self) -> Decimal:
        return Decimal(self.QUANTITY_TOLERANCE)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()
