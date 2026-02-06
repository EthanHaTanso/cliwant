"""
Pytest configuration and fixtures.
"""

import asyncio
from datetime import date, datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_session
from src.main import app
from src.models import Transaction, TransactionStatus, TransactionType


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_transactions(test_session: AsyncSession) -> list[Transaction]:
    """Create sample transactions for testing."""
    transactions = [
        Transaction(
            id="2026-02-05-003-AWS-001",
            bank_name="기업은행",
            account_number="encrypted_123",
            account_number_masked="***-**-789",
            date=datetime(2026, 2, 5),
            time="14:30:00",
            amount=50000,
            type=TransactionType.EXPENSE,
            counterparty="AWS Korea",
            bank_memo="AWS 서버비",
            is_internal_transfer=False,
            is_recurring=True,
            status=TransactionStatus.PENDING_ENRICHMENT,
        ),
        Transaction(
            id="2026-02-05-003-점심-002",
            bank_name="기업은행",
            account_number="encrypted_123",
            account_number_masked="***-**-789",
            date=datetime(2026, 2, 5),
            time="12:00:00",
            amount=12000,
            type=TransactionType.EXPENSE,
            counterparty="점심식대",
            bank_memo="팀 점심",
            is_internal_transfer=False,
            is_recurring=False,
            status=TransactionStatus.PENDING_ENRICHMENT,
        ),
        Transaction(
            id="2026-02-05-020-입금-003",
            bank_name="우리은행",
            account_number="encrypted_456",
            account_number_masked="***-**-321",
            date=datetime(2026, 2, 5),
            time="10:00:00",
            amount=5000000,
            type=TransactionType.INCOME,
            counterparty="매출입금",
            bank_memo="서비스 매출",
            is_internal_transfer=False,
            is_recurring=False,
            status=TransactionStatus.ENRICHED,
        ),
    ]

    for tx in transactions:
        test_session.add(tx)

    await test_session.commit()

    return transactions
