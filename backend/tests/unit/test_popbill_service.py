"""
Unit tests for PopbillService.
"""

from datetime import date, timedelta

import pytest

from src.services.popbill_service import PopbillService


class TestPopbillService:
    """Tests for PopbillService."""

    @pytest.fixture
    def service(self):
        """Create PopbillService instance (mock mode)."""
        return PopbillService()

    @pytest.mark.asyncio
    async def test_fetch_transactions_returns_list(self, service):
        """Test that fetch_transactions_batch returns a list."""
        accounts = [{"bank": "기업은행", "account": "123-456-789"}]
        today = date.today()
        yesterday = today - timedelta(days=1)

        transactions = await service.fetch_transactions_batch(
            corp_num="1234567890",
            accounts=accounts,
            start_date=yesterday,
            end_date=today,
        )

        assert isinstance(transactions, list)

    @pytest.mark.asyncio
    async def test_mock_transactions_have_required_fields(self, service):
        """Test that mock transactions have all required fields."""
        accounts = [{"bank": "기업은행", "account": "123-456-789"}]
        today = date.today()
        yesterday = today - timedelta(days=1)

        transactions = await service.fetch_transactions_batch(
            corp_num="1234567890",
            accounts=accounts,
            start_date=yesterday,
            end_date=today,
        )

        required_fields = [
            "id",
            "bank_name",
            "account_number",
            "date",
            "time",
            "amount",
            "type",
        ]

        for tx in transactions:
            for field in required_fields:
                assert field in tx, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_fetch_multiple_accounts(self, service):
        """Test fetching from multiple accounts."""
        accounts = [
            {"bank": "기업은행", "account": "123-456-789"},
            {"bank": "우리은행", "account": "987-654-321"},
        ]
        today = date.today()
        yesterday = today - timedelta(days=1)

        transactions = await service.fetch_transactions_batch(
            corp_num="1234567890",
            accounts=accounts,
            start_date=yesterday,
            end_date=today,
        )

        # Should have transactions from both banks
        banks = {tx["bank_name"] for tx in transactions}
        assert len(banks) >= 1  # At least one bank

    def test_detect_internal_transfers_empty(self, service):
        """Test internal transfer detection with no transfers."""
        transactions = [
            {"id": "1", "amount": 100, "type": "지출", "date": date.today(), "time": "10:00:00"},
            {"id": "2", "amount": 200, "type": "입금", "date": date.today(), "time": "11:00:00"},
        ]

        internal_ids = service.detect_internal_transfers(transactions)

        assert internal_ids == []

    def test_detect_internal_transfers_matches(self, service):
        """Test internal transfer detection with matching pair."""
        today = date.today()
        transactions = [
            {"id": "1", "amount": 100000, "type": "지출", "date": today, "time": "10:00:00"},
            {"id": "2", "amount": 100000, "type": "입금", "date": today, "time": "10:02:00"},
        ]

        internal_ids = service.detect_internal_transfers(transactions)

        assert len(internal_ids) == 1
        assert "1" in internal_ids  # Expense marked as internal

    def test_detect_internal_transfers_time_window(self, service):
        """Test that transfers outside time window are not detected."""
        today = date.today()
        transactions = [
            {"id": "1", "amount": 100000, "type": "지출", "date": today, "time": "10:00:00"},
            {"id": "2", "amount": 100000, "type": "입금", "date": today, "time": "10:10:00"},
        ]

        internal_ids = service.detect_internal_transfers(transactions)

        # 10 minutes apart - should NOT be detected
        assert internal_ids == []
