"""
Popbill API service for fetching bank transactions.

Includes mock implementation for development without actual API credentials.
"""

import asyncio
import random
from datetime import date, datetime, timedelta
from typing import Optional

from src.config import get_settings


# Bank codes for Popbill API
BANK_CODES = {
    "기업은행": "003",
    "우리은행": "020",
    "국민은행": "004",
    "하나은행": "081",
}

# Reverse mapping
BANK_NAMES = {v: k for k, v in BANK_CODES.items()}


class PopbillService:
    """
    Popbill API service for bank transaction fetching.

    When API credentials are not configured, uses mock implementation
    that generates realistic test data.
    """

    def __init__(
        self,
        link_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        is_test: bool = True,
    ):
        settings = get_settings()
        self.link_id = link_id or settings.popbill_link_id
        self.secret_key = secret_key or settings.popbill_secret_key
        self.is_test = is_test
        self.is_mock = not (self.link_id and self.secret_key)

        if not self.is_mock:
            # Initialize real Popbill service
            try:
                from popbill import EasyFinBankService

                self.service = EasyFinBankService(self.link_id, self.secret_key)
                self.service.IsTest = is_test
            except ImportError:
                self.is_mock = True

    async def fetch_transactions_batch(
        self,
        corp_num: str,
        accounts: list[dict],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Fetch transactions from multiple accounts in parallel.

        Args:
            corp_num: Corporation registration number
            accounts: List of account configs [{"bank": "기업은행", "account": "123-456"}]
            start_date: Start date for query
            end_date: End date for query

        Returns:
            List of transaction dictionaries
        """
        if self.is_mock:
            return await self._fetch_mock_transactions(accounts, start_date, end_date)

        # Real implementation - parallel fetch from all accounts
        tasks = [
            self._fetch_single_account(corp_num, acc, start_date, end_date) for acc in accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        transactions = []
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other accounts
                print(f"Error fetching account: {result}")
                continue
            transactions.extend(result)

        return transactions

    async def _fetch_single_account(
        self,
        corp_num: str,
        account: dict,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch transactions from a single account using Popbill API."""
        bank_code = BANK_CODES.get(account["bank"])
        if not bank_code:
            raise ValueError(f"Unknown bank: {account['bank']}")

        # Run sync Popbill call in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.service.search(
                CorpNum=corp_num,
                BankCode=bank_code,
                AccountNumber=account["account"],
                SDate=start_date.strftime("%Y%m%d"),
                EDate=end_date.strftime("%Y%m%d"),
                Order="D",  # Descending
            ),
        )

        return self._parse_transactions(response, account)

    def _parse_transactions(self, response: dict, account: dict) -> list[dict]:
        """Parse Popbill API response into transaction dictionaries."""
        transactions = []

        for item in response.get("list", []):
            tx_date = datetime.strptime(item["trdate"], "%Y%m%d")
            tx_time = item.get("trtime", "00:00:00")

            # Generate unique ID
            tx_id = self._generate_transaction_id(
                tx_date,
                account["bank"],
                item.get("remark", ""),
                len(transactions),
            )

            # Determine type based on amount
            amount = int(item.get("tramt", 0))
            tx_type = "입금" if item.get("accIn") else "지출"

            transactions.append(
                {
                    "id": tx_id,
                    "bank_name": account["bank"],
                    "account_number": account["account"],
                    "date": tx_date,
                    "time": tx_time,
                    "amount": abs(amount),
                    "type": tx_type,
                    "counterparty": item.get("remark", ""),
                    "bank_memo": item.get("memo", ""),
                }
            )

        return transactions

    async def _fetch_mock_transactions(
        self,
        accounts: list[dict],
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Generate mock transactions for testing.

        Creates realistic transaction data when Popbill API is not configured.
        """
        # Simulate API delay
        await asyncio.sleep(0.5)

        mock_transactions = []
        transaction_counter = {}

        # Sample transaction templates
        templates = [
            # Recurring expenses
            {"counterparty": "AWS Korea", "amount": 50000, "type": "지출", "recurring": True},
            {"counterparty": "네이버클라우드", "amount": 30000, "type": "지출", "recurring": True},
            {"counterparty": "급여이체", "amount": 3500000, "type": "지출", "recurring": True},
            {"counterparty": "사무실월세", "amount": 1200000, "type": "지출", "recurring": True},
            # Non-recurring expenses
            {"counterparty": "카페 미팅비", "amount": 25000, "type": "지출", "recurring": False},
            {"counterparty": "택시비", "amount": 15000, "type": "지출", "recurring": False},
            {"counterparty": "사무용품", "amount": 45000, "type": "지출", "recurring": False},
            {"counterparty": "점심식대", "amount": 12000, "type": "지출", "recurring": False},
            {"counterparty": "마케팅비", "amount": 200000, "type": "지출", "recurring": False},
            {"counterparty": "교육비", "amount": 100000, "type": "지출", "recurring": False},
            # Income
            {"counterparty": "매출입금", "amount": 5000000, "type": "입금", "recurring": False},
            {"counterparty": "서비스료", "amount": 1500000, "type": "입금", "recurring": False},
        ]

        # Generate transactions for each day in range
        current_date = start_date
        while current_date <= end_date:
            # Generate 2-5 transactions per day
            num_transactions = random.randint(2, 5)

            for _ in range(num_transactions):
                template = random.choice(templates)
                account = random.choice(accounts)

                # Add some variation to amounts
                amount_variation = random.uniform(0.9, 1.1)
                amount = int(template["amount"] * amount_variation)

                # Generate unique ID
                bank_code = BANK_CODES.get(account["bank"], "000")
                key = f"{current_date.strftime('%Y-%m-%d')}-{bank_code}"
                transaction_counter[key] = transaction_counter.get(key, 0) + 1

                tx_id = f"{current_date.strftime('%Y-%m-%d')}-{bank_code}-{template['counterparty'][:3]}-{transaction_counter[key]:03d}"

                # Random time
                hour = random.randint(9, 18)
                minute = random.randint(0, 59)
                tx_time = f"{hour:02d}:{minute:02d}:00"

                mock_transactions.append(
                    {
                        "id": tx_id,
                        "bank_name": account["bank"],
                        "account_number": account.get("account", "123-456-789"),
                        "date": datetime.combine(current_date, datetime.min.time()),
                        "time": tx_time,
                        "amount": amount,
                        "type": template["type"],
                        "counterparty": template["counterparty"],
                        "bank_memo": f"Mock: {template['counterparty']}",
                    }
                )

            current_date += timedelta(days=1)

        return mock_transactions

    def _generate_transaction_id(
        self,
        tx_date: datetime,
        bank_name: str,
        counterparty: str,
        index: int,
    ) -> str:
        """Generate unique transaction ID."""
        bank_code = BANK_CODES.get(bank_name, "000")
        party_code = counterparty[:3] if counterparty else "UNK"
        return f"{tx_date.strftime('%Y-%m-%d')}-{bank_code}-{party_code}-{index:03d}"

    def detect_internal_transfers(self, transactions: list[dict]) -> list[str]:
        """
        Detect internal transfers between accounts.

        Identifies pairs of transactions with:
        - Same amount
        - Same time window (±5 minutes)
        - One income, one expense

        Returns:
            List of transaction IDs to exclude (duplicates)
        """
        internal_transfer_ids = []

        # Group transactions by amount
        by_amount: dict[int, list[dict]] = {}
        for tx in transactions:
            amount = tx["amount"]
            if amount not in by_amount:
                by_amount[amount] = []
            by_amount[amount].append(tx)

        # Find matching pairs
        for amount, txs in by_amount.items():
            if len(txs) < 2:
                continue

            incomes = [tx for tx in txs if tx["type"] == "입금"]
            expenses = [tx for tx in txs if tx["type"] == "지출"]

            for income in incomes:
                for expense in expenses:
                    # Check if same date (handle both datetime and date objects)
                    income_date = income["date"].date() if hasattr(income["date"], 'date') else income["date"]
                    expense_date = expense["date"].date() if hasattr(expense["date"], 'date') else expense["date"]
                    if income_date != expense_date:
                        continue

                    # Check time window (±5 minutes)
                    try:
                        income_time = datetime.strptime(income["time"], "%H:%M:%S")
                        expense_time = datetime.strptime(expense["time"], "%H:%M:%S")
                        time_diff = abs((income_time - expense_time).total_seconds())

                        if time_diff <= 300:  # 5 minutes
                            # Mark one as internal transfer (keep income, mark expense)
                            internal_transfer_ids.append(expense["id"])
                    except (ValueError, TypeError):
                        continue

        return internal_transfer_ids
