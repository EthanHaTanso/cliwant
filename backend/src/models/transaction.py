"""
Transaction model for storing bank transaction data.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.enriched_context import EnrichedContext


class TransactionType(str, enum.Enum):
    """Transaction type - income or expense."""

    INCOME = "입금"
    EXPENSE = "지출"


class TransactionStatus(str, enum.Enum):
    """Transaction processing status."""

    PENDING_ENRICHMENT = "pending_enrichment"  # 맥락 입력 대기
    ENRICHED = "enriched"  # 맥락 입력 완료
    PENDING_MANUAL_REVIEW = "pending_manual_review"  # 수동 확인 필요
    AUTO_CLASSIFIED = "auto_classified"  # 자동 분류됨


class Transaction(Base):
    """
    Bank transaction record.

    Stores transaction data fetched from Popbill API.
    Each transaction can have an associated EnrichedContext.
    """

    __tablename__ = "transactions"

    # Primary Key - Format: "2026-02-05-IBK-AWS-001"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Bank Info
    bank_name: Mapped[str] = mapped_column(String(50), nullable=False)  # "기업은행"
    account_number: Mapped[str] = mapped_column(String(255), nullable=False)  # 암호화 저장
    account_number_masked: Mapped[str] = mapped_column(String(50))  # "***-**-789"

    # Transaction Details
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    time: Mapped[Optional[str]] = mapped_column(String(10))  # "14:30:00"
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 원 단위
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    counterparty: Mapped[Optional[str]] = mapped_column(String(255))  # "AWS Korea"
    bank_memo: Mapped[Optional[str]] = mapped_column(Text)  # 은행 앱 메모

    # Classification
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING_ENRICHMENT
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    enriched_context: Mapped[Optional["EnrichedContext"]] = relationship(
        "EnrichedContext", back_populates="transaction", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id}: {self.counterparty} {self.amount:,}원 {self.type.value}>"
