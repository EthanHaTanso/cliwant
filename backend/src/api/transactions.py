"""
Transaction API endpoints (US-001).

Handles transaction syncing, listing, and retrieval.
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import Transaction, TransactionStatus, TransactionType
from src.services.popbill_service import PopbillService
from src.utils import encrypt_value, mask_account_number

router = APIRouter(prefix="/transactions", tags=["transactions"])


# === Pydantic Models ===


class AccountConfig(BaseModel):
    """Bank account configuration."""

    bank: str
    account: str


class SyncTransactionsRequest(BaseModel):
    """Request body for syncing transactions."""

    start_date: date
    end_date: date
    accounts: Optional[list[AccountConfig]] = None


class SyncTransactionsResponse(BaseModel):
    """Response for sync transactions endpoint."""

    status: str
    new_transactions: int
    total_transactions: int
    internal_transfers_detected: int


class TransactionResponse(BaseModel):
    """Single transaction response."""

    id: str
    bank_name: str
    account_number_masked: str
    date: datetime
    time: Optional[str]
    amount: int
    type: str
    counterparty: Optional[str]
    bank_memo: Optional[str]
    is_internal_transfer: bool
    is_recurring: bool
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Response for list transactions endpoint."""

    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


# === Helper Functions ===


def transaction_to_response(tx: Transaction) -> TransactionResponse:
    """Convert Transaction model to response."""
    return TransactionResponse(
        id=tx.id,
        bank_name=tx.bank_name,
        account_number_masked=tx.account_number_masked or "",
        date=tx.date,
        time=tx.time,
        amount=tx.amount,
        type=tx.type.value,
        counterparty=tx.counterparty,
        bank_memo=tx.bank_memo,
        is_internal_transfer=tx.is_internal_transfer,
        is_recurring=tx.is_recurring,
        status=tx.status.value,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


# === Endpoints ===


@router.post("/sync", response_model=SyncTransactionsResponse)
async def sync_transactions(
    request: SyncTransactionsRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Sync transactions from Popbill API.

    - Fetches transactions from all configured accounts
    - Detects and marks internal transfers
    - Saves new transactions to database
    - Skips duplicates based on transaction ID

    AC-001-01, AC-001-02, AC-001-03
    """
    popbill = PopbillService()

    # Use provided accounts or default mock accounts
    accounts = [{"bank": acc.bank, "account": acc.account} for acc in (request.accounts or [])]

    if not accounts:
        # Default mock accounts for testing
        accounts = [
            {"bank": "기업은행", "account": "123-456-789"},
            {"bank": "우리은행", "account": "987-654-321"},
        ]

    # Fetch transactions from Popbill (or mock)
    raw_transactions = await popbill.fetch_transactions_batch(
        corp_num="1234567890",  # Would come from UserConfig
        accounts=accounts,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    # Detect internal transfers
    internal_transfer_ids = popbill.detect_internal_transfers(raw_transactions)

    # Save to database
    new_count = 0
    for tx_data in raw_transactions:
        # Check if already exists
        existing = await session.get(Transaction, tx_data["id"])
        if existing:
            continue

        # Create new transaction
        transaction = Transaction(
            id=tx_data["id"],
            bank_name=tx_data["bank_name"],
            account_number=encrypt_value(tx_data["account_number"]),
            account_number_masked=mask_account_number(tx_data["account_number"]),
            date=tx_data["date"],
            time=tx_data["time"],
            amount=tx_data["amount"],
            type=TransactionType(tx_data["type"]),
            counterparty=tx_data.get("counterparty"),
            bank_memo=tx_data.get("bank_memo"),
            is_internal_transfer=tx_data["id"] in internal_transfer_ids,
            status=TransactionStatus.PENDING_ENRICHMENT,
        )

        session.add(transaction)
        new_count += 1

    await session.commit()

    # Get total count
    total_result = await session.execute(select(func.count(Transaction.id)))
    total_count = total_result.scalar() or 0

    return SyncTransactionsResponse(
        status="success",
        new_transactions=new_count,
        total_transactions=total_count,
        internal_transfers_detected=len(internal_transfer_ids),
    )


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    month: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    bank: Optional[str] = Query(None, description="Filter by bank name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    List transactions with optional filters.

    Supports filtering by month, status, and bank.
    Returns paginated results.
    """
    # Build query
    query = select(Transaction)

    # Apply filters
    if month:
        # Filter by year-month
        try:
            year, mon = month.split("-")
            start = datetime(int(year), int(mon), 1)
            if int(mon) == 12:
                end = datetime(int(year) + 1, 1, 1)
            else:
                end = datetime(int(year), int(mon) + 1, 1)
            query = query.where(Transaction.date >= start, Transaction.date < end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    if status:
        try:
            status_enum = TransactionStatus(status)
            query = query.where(Transaction.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if bank:
        query = query.where(Transaction.bank_name == bank)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(Transaction.date.desc(), Transaction.time.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await session.execute(query)
    transactions = result.scalars().all()

    return TransactionListResponse(
        transactions=[transaction_to_response(tx) for tx in transactions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/pending", response_model=list[TransactionResponse])
async def get_pending_transactions(
    session: AsyncSession = Depends(get_session),
):
    """
    Get transactions pending enrichment.

    Returns transactions with status 'pending_enrichment'.
    Used for generating smart questions.

    AC-001-04
    """
    query = (
        select(Transaction)
        .where(Transaction.status == TransactionStatus.PENDING_ENRICHMENT)
        .where(Transaction.is_internal_transfer == False)  # noqa: E712
        .order_by(Transaction.date.desc())
    )

    result = await session.execute(query)
    transactions = result.scalars().all()

    return [transaction_to_response(tx) for tx in transactions]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single transaction by ID.
    """
    transaction = await session.get(Transaction, transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction_to_response(transaction)
