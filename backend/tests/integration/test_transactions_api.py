"""
Integration tests for Transaction API.
"""

from datetime import date

import pytest
from httpx import AsyncClient


class TestTransactionsAPI:
    """Integration tests for /api/v1/transactions endpoints."""

    @pytest.mark.asyncio
    async def test_sync_transactions(self, client: AsyncClient):
        """Test syncing transactions from mock Popbill API."""
        response = await client.post(
            "/api/v1/transactions/sync",
            json={
                "start_date": "2026-02-01",
                "end_date": "2026-02-05",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["new_transactions"] >= 0
        assert data["total_transactions"] >= 0

    @pytest.mark.asyncio
    async def test_sync_transactions_with_accounts(self, client: AsyncClient):
        """Test syncing with specific accounts."""
        response = await client.post(
            "/api/v1/transactions/sync",
            json={
                "start_date": "2026-02-01",
                "end_date": "2026-02-02",
                "accounts": [
                    {"bank": "기업은행", "account": "111-222-333"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_list_transactions_empty(self, client: AsyncClient):
        """Test listing transactions when empty."""
        response = await client.get("/api/v1/transactions/")

        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_transactions_with_data(
        self, client: AsyncClient, sample_transactions
    ):
        """Test listing transactions with sample data."""
        response = await client.get("/api/v1/transactions/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["transactions"]) == 3

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_month(
        self, client: AsyncClient, sample_transactions
    ):
        """Test filtering transactions by month."""
        response = await client.get("/api/v1/transactions/?month=2026-02")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_status(
        self, client: AsyncClient, sample_transactions
    ):
        """Test filtering transactions by status."""
        response = await client.get(
            "/api/v1/transactions/?status=pending_enrichment"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # 2 pending, 1 enriched

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_bank(
        self, client: AsyncClient, sample_transactions
    ):
        """Test filtering transactions by bank."""
        response = await client.get("/api/v1/transactions/?bank=기업은행")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_transactions_pagination(
        self, client: AsyncClient, sample_transactions
    ):
        """Test pagination."""
        response = await client.get("/api/v1/transactions/?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2

    @pytest.mark.asyncio
    async def test_get_single_transaction(
        self, client: AsyncClient, sample_transactions
    ):
        """Test getting a single transaction."""
        tx_id = sample_transactions[0].id
        response = await client.get(f"/api/v1/transactions/{tx_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tx_id
        assert data["amount"] == 50000
        assert data["counterparty"] == "AWS Korea"

    @pytest.mark.asyncio
    async def test_get_single_transaction_not_found(self, client: AsyncClient):
        """Test getting non-existent transaction."""
        response = await client.get("/api/v1/transactions/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pending_transactions(
        self, client: AsyncClient, sample_transactions
    ):
        """Test getting pending transactions."""
        response = await client.get("/api/v1/transactions/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # 2 pending_enrichment transactions

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "AI Tax Assistant"
