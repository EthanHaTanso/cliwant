"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/ai_tax_assistant.db"

    # Popbill API
    popbill_link_id: str = ""
    popbill_secret_key: str = ""
    popbill_corp_num: str = ""
    popbill_is_test: bool = True

    # Slack API
    slack_bot_token: str = ""
    slack_channel_id: str = ""
    slack_signing_secret: str = ""

    # Anthropic API
    anthropic_api_key: str = ""

    # Email (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Security
    encryption_key: str = ""

    # File Storage
    documents_path: str = "~/ai-tax-assistant/documents"

    @property
    def documents_dir(self) -> Path:
        """Get resolved documents directory path."""
        return Path(self.documents_path).expanduser()

    def is_popbill_configured(self) -> bool:
        """Check if Popbill API is configured."""
        return bool(self.popbill_link_id and self.popbill_secret_key)

    def is_slack_configured(self) -> bool:
        """Check if Slack API is configured."""
        return bool(self.slack_bot_token and self.slack_channel_id)

    def is_anthropic_configured(self) -> bool:
        """Check if Anthropic API is configured."""
        return bool(self.anthropic_api_key)

    def is_smtp_configured(self) -> bool:
        """Check if SMTP is configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
