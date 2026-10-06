from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "Bisb — Competitive Monitor"
    environment: str = "development"
    database_url: SecretStr
    gnews_api_key: SecretStr | None = None
    analysis_provider: Literal["gemini", "mock"] = "mock"
    gemini_model: str = "gemini-3.8-flash"
    gemini_api_key: SecretStr | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        url = value.get_secret_value()
        PostgresDsn(url)
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL deve usar postgresql+psycopg://")
        return value
