"""Configuration management for the Solver application."""


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

    # AI Provider (OpenAI-compatible: DeepSeek, OpenAI, etc.)
    ai_api_key: str = ""
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-chat"
    ai_deep_model: str = "deepseek-reasoner"

    # Backward compatibility with old OPENAI_* env vars
    @property
    def openai_api_key(self) -> str:
        """Backward-compat: prefer AI_API_KEY, fall back to OPENAI_API_KEY."""
        return self.ai_api_key

    @property
    def openai_model(self) -> str:
        """Backward-compat: prefer AI_MODEL, fall back to OPENAI_MODEL."""
        return self.ai_model

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
