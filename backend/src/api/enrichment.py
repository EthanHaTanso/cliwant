"""
Enrichment API endpoints (US-002, US-003).

Handles smart questions generation, answer submission, and context storage.
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_session
from src.models import EnrichedContext, Transaction, TransactionStatus
from src.services.ai_service import AIService

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


# === Pydantic Models ===


class GenerateQuestionsRequest(BaseModel):
    """Request for generating smart questions."""

    transaction_id: str


class QuestionOption(BaseModel):
    """Single question with options."""

    id: str
    text: str
    options: list[str]
    type: str  # single_choice, multiple_choice, text, file_upload


class GenerateQuestionsResponse(BaseModel):
    """Response with generated questions."""

    transaction_id: str
    questions: list[QuestionOption]
    confidence: float
    category_suggestion: Optional[str] = None


class AnswerItem(BaseModel):
    """Single answer to a question."""

    question_id: str
    answer: str


class SubmitAnswersRequest(BaseModel):
    """Request for submitting answers."""

    transaction_id: str
    answers: list[AnswerItem]


class SubmitAnswersResponse(BaseModel):
    """Response after submitting answers."""

    status: str
    enriched_context_id: str
    ai_summary: Optional[str] = None


class EnrichedContextResponse(BaseModel):
    """Enriched context data."""

    id: str
    transaction_id: str
    user_memo: Optional[str]
    category: Optional[str]
    account_classification: Optional[str]
    is_recurring: bool
    frequency: Optional[str]
    related_transaction_ids: list[str]
    tax_notes: Optional[str]
    ai_generated_summary: Optional[str]
    documents: dict
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    """Response after file upload."""

    status: str
    file_path: str
    file_name: str


# === Helper Functions ===


def context_to_response(ctx: EnrichedContext) -> EnrichedContextResponse:
    """Convert EnrichedContext model to response."""
    return EnrichedContextResponse(
        id=ctx.id,
        transaction_id=ctx.transaction_id,
        user_memo=ctx.user_memo,
        category=ctx.category,
        account_classification=ctx.account_classification,
        is_recurring=ctx.is_recurring,
        frequency=ctx.frequency,
        related_transaction_ids=ctx.related_transaction_ids or [],
        tax_notes=ctx.tax_notes,
        ai_generated_summary=ctx.ai_generated_summary,
        documents=ctx.documents or {},
        created_at=ctx.created_at,
        updated_at=ctx.updated_at,
    )


# === Endpoints ===


@router.post("/questions", response_model=GenerateQuestionsResponse)
async def generate_questions(
    request: GenerateQuestionsRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Generate smart questions for a transaction.

    Uses AI (Claude) to generate tax-law based questions.
    Falls back to templates when AI is not configured.

    AC-002-01
    """
    # Get transaction
    transaction = await session.get(Transaction, request.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Prepare transaction data for AI
    tx_data = {
        "id": transaction.id,
        "date": transaction.date.strftime("%Y-%m-%d"),
        "time": transaction.time or "",
        "amount": transaction.amount,
        "type": transaction.type.value,
        "counterparty": transaction.counterparty or "",
        "bank_memo": transaction.bank_memo or "",
        "bank_name": transaction.bank_name,
    }

    # Find past patterns (similar transactions)
    past_query = (
        select(Transaction)
        .where(Transaction.counterparty == transaction.counterparty)
        .where(Transaction.id != transaction.id)
        .order_by(Transaction.date.desc())
        .limit(5)
    )
    past_result = await session.execute(past_query)
    past_transactions = past_result.scalars().all()

    past_patterns = [
        {
            "date": tx.date.strftime("%Y-%m-%d"),
            "amount": tx.amount,
            "counterparty": tx.counterparty,
        }
        for tx in past_transactions
    ]

    # Generate questions
    ai_service = AIService()
    result = await ai_service.generate_smart_questions(tx_data, past_patterns)

    questions = [
        QuestionOption(
            id=q["id"],
            text=q["text"],
            options=q["options"],
            type=q.get("type", "single_choice"),
        )
        for q in result.get("questions", [])
    ]

    return GenerateQuestionsResponse(
        transaction_id=request.transaction_id,
        questions=questions,
        confidence=result.get("confidence", 0.7),
        category_suggestion=result.get("category_suggestion"),
    )


@router.post("/answers", response_model=SubmitAnswersResponse)
async def submit_answers(
    request: SubmitAnswersRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Submit answers and create EnrichedContext.

    Generates AI summary and updates transaction status.

    AC-002-03, AC-003-01, AC-003-02
    """
    # Get transaction
    transaction = await session.get(Transaction, request.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Check if context already exists
    existing_query = select(EnrichedContext).where(
        EnrichedContext.transaction_id == request.transaction_id
    )
    existing_result = await session.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="EnrichedContext already exists for this transaction",
        )

    # Prepare data for AI summary
    tx_data = {
        "date": transaction.date.strftime("%Y-%m-%d"),
        "amount": transaction.amount,
        "type": transaction.type.value,
        "counterparty": transaction.counterparty or "",
        "bank_memo": transaction.bank_memo or "",
    }
    answers_data = [{"question_id": a.question_id, "answer": a.answer} for a in request.answers]

    # Generate AI summary
    ai_service = AIService()
    summary_result = await ai_service.generate_ai_summary(tx_data, answers_data)

    # Extract answers
    is_recurring = any(
        "매월" in a.answer or "매주" in a.answer
        for a in request.answers
        if a.question_id == "Q2"
    )
    frequency = next(
        (a.answer for a in request.answers if a.question_id == "Q2" and is_recurring),
        None,
    )

    # Check document status from answers
    doc_received = any(
        "받았" in a.answer for a in request.answers if a.question_id == "Q4"
    )
    doc_status = "✅ 준비 완료" if doc_received else "⚠️ 준비 필요"

    # Create EnrichedContext
    context_id = f"EC-{transaction.date.strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:6]}"

    enriched_context = EnrichedContext(
        id=context_id,
        transaction_id=transaction.id,
        user_memo=transaction.bank_memo,
        category=summary_result.get("account_classification"),
        account_classification=summary_result.get("account_classification"),
        is_recurring=is_recurring,
        frequency=frequency,
        related_transaction_ids=[],
        tax_notes=summary_result.get("tax_notes"),
        ai_generated_summary=summary_result.get("summary"),
        documents={
            "invoice_received": doc_received,
            "files": [],
            "status": doc_status,
        },
    )

    session.add(enriched_context)

    # Update transaction status
    transaction.status = TransactionStatus.ENRICHED
    transaction.is_recurring = is_recurring

    await session.commit()

    return SubmitAnswersResponse(
        status="success",
        enriched_context_id=context_id,
        ai_summary=summary_result.get("summary"),
    )


@router.post("/files/{transaction_id}", response_model=FileUploadResponse)
async def upload_document(
    transaction_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload document file for a transaction.

    Saves file to local storage and updates EnrichedContext.

    AC-002-05
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Check file extension
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}",
        )

    # Check file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    # Get transaction
    transaction = await session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Create storage directory
    settings = get_settings()
    docs_dir = settings.documents_dir
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    date_str = transaction.date.strftime("%Y-%m-%d")
    new_filename = f"invoice_{transaction_id}_{date_str}{ext}"
    file_path = docs_dir / new_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Update EnrichedContext if exists
    context_query = select(EnrichedContext).where(
        EnrichedContext.transaction_id == transaction_id
    )
    context_result = await session.execute(context_query)
    context = context_result.scalar_one_or_none()

    if context:
        docs = context.documents or {"invoice_received": False, "files": [], "status": "⚠️ 준비 필요"}
        docs["files"].append(str(file_path))
        docs["invoice_received"] = True
        docs["status"] = "✅ 준비 완료"
        context.documents = docs
        await session.commit()

    return FileUploadResponse(
        status="success",
        file_path=str(file_path),
        file_name=new_filename,
    )


@router.get("/context/{transaction_id}", response_model=EnrichedContextResponse)
async def get_enriched_context(
    transaction_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get EnrichedContext for a transaction.

    AC-003-01
    """
    query = select(EnrichedContext).where(EnrichedContext.transaction_id == transaction_id)
    result = await session.execute(query)
    context = result.scalar_one_or_none()

    if not context:
        raise HTTPException(status_code=404, detail="EnrichedContext not found")

    return context_to_response(context)


@router.put("/context/{transaction_id}", response_model=EnrichedContextResponse)
async def update_enriched_context(
    transaction_id: str,
    updates: dict,
    session: AsyncSession = Depends(get_session),
):
    """
    Update EnrichedContext.

    AC-003-03 - Related transaction linking
    """
    query = select(EnrichedContext).where(EnrichedContext.transaction_id == transaction_id)
    result = await session.execute(query)
    context = result.scalar_one_or_none()

    if not context:
        raise HTTPException(status_code=404, detail="EnrichedContext not found")

    # Update allowed fields
    allowed_fields = [
        "user_memo",
        "category",
        "account_classification",
        "is_recurring",
        "frequency",
        "related_transaction_ids",
        "tax_notes",
    ]

    for field in allowed_fields:
        if field in updates:
            setattr(context, field, updates[field])

    # Handle bidirectional linking for related transactions
    if "related_transaction_ids" in updates:
        new_related = updates["related_transaction_ids"]
        for related_id in new_related:
            # Get related context
            related_query = select(EnrichedContext).where(
                EnrichedContext.transaction_id == related_id
            )
            related_result = await session.execute(related_query)
            related_context = related_result.scalar_one_or_none()

            if related_context:
                # Add bidirectional link
                related_ids = related_context.related_transaction_ids or []
                if transaction_id not in related_ids:
                    related_ids.append(transaction_id)
                    related_context.related_transaction_ids = related_ids

    await session.commit()
    await session.refresh(context)

    return context_to_response(context)
