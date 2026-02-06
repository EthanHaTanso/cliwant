"""
EnrichedContext model for storing transaction context and metadata.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.transaction import Transaction


class EnrichedContext(Base):
    """
    Enriched context for a transaction.

    Stores user-provided context, AI-generated summaries, and document information.
    One-to-one relationship with Transaction.
    """

    __tablename__ = "enriched_contexts"

    # Primary Key - Format: "EC-2026-02-05-001"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Foreign Key
    transaction_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("transactions.id"), unique=True
    )

    # User Input
    user_memo: Mapped[Optional[str]] = mapped_column(String(500))  # "AWS 서버비"
    category: Mapped[Optional[str]] = mapped_column(String(100))  # "개발비 - 클라우드 운영"
    account_classification: Mapped[Optional[str]] = mapped_column(String(100))  # "경비 - 통신비"

    # Pattern Info
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[Optional[str]] = mapped_column(String(100))  # "월 1회, 매월 15일"
    related_transaction_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )  # ["2026-01-15-IBK-AWS"]

    # Tax Info
    tax_notes: Mapped[Optional[str]] = mapped_column(Text)  # "연구개발비 세액공제 대상"

    # AI Generated
    ai_generated_summary: Mapped[Optional[str]] = mapped_column(Text)

    # Documents - JSON structure:
    # {
    #   "invoice_received": bool,
    #   "files": ["path1.pdf", "path2.jpg"],
    #   "status": "✅ 준비 완료" | "⚠️ 준비 필요" | "❌ 증빙 불가"
    # }
    documents: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "invoice_received": False,
            "files": [],
            "status": "⚠️ 준비 필요",
        },
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="enriched_context"
    )

    def __repr__(self) -> str:
        return f"<EnrichedContext {self.id}: {self.category}>"
