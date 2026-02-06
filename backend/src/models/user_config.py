"""
UserConfig model for storing user settings.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class UserConfig(Base):
    """
    User configuration and settings.

    Stores Popbill API credentials, bank accounts, Slack settings, etc.
    Single user application - uses 'default' as the primary key.
    """

    __tablename__ = "user_configs"

    # Primary Key
    id: Mapped[str] = mapped_column(String(100), primary_key=True, default="default")

    # Popbill Settings (암호화 저장)
    popbill_api_key_encrypted: Mapped[Optional[str]] = mapped_column(String(500))
    popbill_secret_key_encrypted: Mapped[Optional[str]] = mapped_column(String(500))
    popbill_corp_num: Mapped[Optional[str]] = mapped_column(String(20))

    # Bank Accounts - JSON array:
    # [
    #   {"bank": "기업은행", "account_number_encrypted": "...", "popbill_quick_query": true},
    #   {"bank": "우리은행", "account_number_encrypted": "...", "popbill_quick_query": true}
    # ]
    accounts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Query Settings
    query_interval: Mapped[str] = mapped_column(String(20), default="daily")

    # Slack Settings
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(String(500))
    slack_channel_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Accountant Settings
    accountant_email: Mapped[Optional[str]] = mapped_column(String(255))
    accountant_format: Mapped[str] = mapped_column(String(10), default="xlsx")  # xlsx, csv, pdf

    # File Storage - None = auto (home directory based)
    documents_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserConfig {self.id}: {len(self.accounts)} accounts>"
