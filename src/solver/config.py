"""Configuration management for the Solver application."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_deep_model: str = "gpt-4o"

    # Database
    database_url: str = "sqlite+aiosqlite:///solver.db"

    # Scheduler
    proactive_check_interval_minutes: int = 60
    default_check_in_hour: int = 9

    # Logging
    log_level: str = "INFO"

    @property
    def is_configured(self) -> bool:
        """Check if the essential configuration is provided."""
        return bool(self.telegram_bot_token and self.openai_api_key)


def get_settings() -> Settings:
    """Factory function to get application settings."""
    return Settings()
