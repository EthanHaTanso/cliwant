"""
MonthlyDocument model for storing generated tax documents.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status."""

    GENERATED = "generated"  # 생성됨
    REVIEWED = "reviewed"  # 리뷰 완료
    SENT = "sent"  # 세무사에게 발송됨


class MonthlyDocument(Base):
    """
    Monthly tax document.

    Stores auto-generated monthly summary documents for tax reporting.
    """

    __tablename__ = "monthly_documents"

    # Primary Key - Format: "MD-2026-02"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Reference
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    month: Mapped[str] = mapped_column(String(10), nullable=False)  # "2026-02"

    # Summary Stats
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    total_income: Mapped[int] = mapped_column(Integer, default=0)
    total_expense: Mapped[int] = mapped_column(Integer, default=0)
    recurring_count: Mapped[int] = mapped_column(Integer, default=0)
    non_recurring_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)

    # Content
    document_markdown: Mapped[Optional[str]] = mapped_column(Text)
    document_version: Mapped[int] = mapped_column(Integer, default=1)

    # Status
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.GENERATED
    )

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sent_to_accountant_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Accountant Info
    accountant_email: Mapped[Optional[str]] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<MonthlyDocument {self.id}: {self.total_transactions} transactions>"
