"""
Document generation service for monthly tax reports.

Generates markdown documents from transaction data and enriched contexts.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import EnrichedContext, MonthlyDocument, Transaction, TransactionStatus
from src.services.ai_service import AIService


class DocumentService:
    """
    Service for generating monthly tax documents.

    Creates comprehensive markdown documents with:
    - Monthly summary
    - Document checklist
    - Recurring transactions
    - Non-recurring transactions (grouped by relationship)
    - Pending transactions
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ai_service = AIService()

    async def generate_monthly_document(
        self,
        user_id: str,
        year: int,
        month: int,
    ) -> MonthlyDocument:
        """
        Generate monthly document for given month.

        Args:
            user_id: User ID
            year: Year (e.g., 2026)
            month: Month (1-12)

        Returns:
            Generated MonthlyDocument
        """
        # Get date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        month_str = f"{year}-{month:02d}"

        # Fetch all transactions for the month
        query = (
            select(Transaction)
            .where(
                and_(
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                    Transaction.is_internal_transfer == False,  # noqa: E712
                )
            )
            .order_by(Transaction.date)
        )
        result = await self.session.execute(query)
        transactions = result.scalars().all()

        if not transactions:
            # Create empty document
            return await self._create_empty_document(user_id, month_str)

        # Fetch enriched contexts
        tx_ids = [tx.id for tx in transactions]
        context_query = select(EnrichedContext).where(
            EnrichedContext.transaction_id.in_(tx_ids)
        )
        context_result = await self.session.execute(context_query)
        contexts = {ctx.transaction_id: ctx for ctx in context_result.scalars().all()}

        # Categorize transactions
        recurring = [tx for tx in transactions if tx.is_recurring]
        non_recurring = [tx for tx in transactions if not tx.is_recurring and tx.status == TransactionStatus.ENRICHED]
        pending = [tx for tx in transactions if tx.status in (TransactionStatus.PENDING_ENRICHMENT, TransactionStatus.PENDING_MANUAL_REVIEW)]

        # Calculate stats
        income_txs = [tx for tx in transactions if tx.type.value == "입금"]
        expense_txs = [tx for tx in transactions if tx.type.value == "지출"]
        total_income = sum(tx.amount for tx in income_txs)
        total_expense = sum(tx.amount for tx in expense_txs)

        # Generate document sections
        markdown_parts = []

        # Header
        markdown_parts.append(self._generate_header(user_id, month_str, len(transactions)))

        # Monthly Summary
        markdown_parts.append(self._generate_summary(
            total_transactions=len(transactions),
            total_income=total_income,
            total_expense=total_expense,
            income_count=len(income_txs),
            expense_count=len(expense_txs),
            banks=list({tx.bank_name for tx in transactions}),
        ))

        # Document Checklist
        checklist = self._generate_checklist(transactions, contexts)
        markdown_parts.append(checklist["markdown"])

        # Recurring Transactions
        if recurring:
            markdown_parts.append(self._generate_recurring_section(recurring, contexts))

        # Non-recurring Transactions (grouped)
        if non_recurring:
            markdown_parts.append(await self._generate_non_recurring_section(non_recurring, contexts))

        # Pending Transactions
        if pending:
            markdown_parts.append(self._generate_pending_section(pending))

        # Combine all parts
        document_markdown = "\n\n".join(markdown_parts)

        # Create or update MonthlyDocument
        doc_id = f"MD-{month_str}"
        existing = await self.session.get(MonthlyDocument, doc_id)

        if existing:
            existing.document_markdown = document_markdown
            existing.document_version += 1
            existing.total_transactions = len(transactions)
            existing.total_income = total_income
            existing.total_expense = total_expense
            existing.recurring_count = len(recurring)
            existing.non_recurring_count = len(non_recurring)
            existing.pending_count = len(pending)
            existing.generated_at = datetime.utcnow()
            document = existing
        else:
            document = MonthlyDocument(
                id=doc_id,
                user_id=user_id,
                month=month_str,
                total_transactions=len(transactions),
                total_income=total_income,
                total_expense=total_expense,
                recurring_count=len(recurring),
                non_recurring_count=len(non_recurring),
                pending_count=len(pending),
                document_markdown=document_markdown,
            )
            self.session.add(document)

        await self.session.commit()
        return document

    async def _create_empty_document(self, user_id: str, month_str: str) -> MonthlyDocument:
        """Create empty document when no transactions exist."""
        doc_id = f"MD-{month_str}"
        markdown = f"""# {month_str} 입출금 내역 요약

해당 월에 거래 내역이 없습니다.
"""
        document = MonthlyDocument(
            id=doc_id,
            user_id=user_id,
            month=month_str,
            total_transactions=0,
            total_income=0,
            total_expense=0,
            document_markdown=markdown,
        )
        self.session.add(document)
        await self.session.commit()
        return document

    def _generate_header(self, user_id: str, month: str, total: int) -> str:
        """Generate document header."""
        return f"""# {month} 입출금 내역 요약 (총 {total}건)

**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**상태**: 자동 생성됨"""

    def _generate_summary(
        self,
        total_transactions: int,
        total_income: int,
        total_expense: int,
        income_count: int,
        expense_count: int,
        banks: list[str],
    ) -> str:
        """Generate monthly summary section."""
        net_flow = total_income - total_expense
        flow_sign = "+" if net_flow >= 0 else ""

        return f"""## 📊 월별 요약

| 항목 | 금액 | 건수 |
|------|------|------|
| **총 입금** | {total_income:,}원 | {income_count}건 |
| **총 지출** | {total_expense:,}원 | {expense_count}건 |
| **순 현금흐름** | {flow_sign}{net_flow:,}원 | - |

**사용 계좌**: {', '.join(banks)}"""

    def _generate_checklist(
        self,
        transactions: list[Transaction],
        contexts: dict[str, EnrichedContext],
    ) -> dict[str, Any]:
        """Generate document checklist."""
        ready = []
        needs_preparation = []
        not_available = []

        for tx in transactions:
            ctx = contexts.get(tx.id)
            if ctx:
                docs = ctx.documents or {}
                status = docs.get("status", "⚠️ 준비 필요")

                if "✅" in status:
                    ready.append(tx)
                elif "❌" in status:
                    not_available.append(tx)
                else:
                    needs_preparation.append(tx)
            else:
                needs_preparation.append(tx)

        # Build markdown
        markdown = f"""## 📋 증빙 서류 체크리스트

| 상태 | 건수 | 설명 |
|------|------|------|
| ✅ 준비 완료 | {len(ready)}건 | 계산서/영수증 수집 완료 |
| ⚠️ 준비 필요 | {len(needs_preparation)}건 | 계산서 미수령, 요청 필요 |
| ❌ 증빙 불가 | {len(not_available)}건 | 개인 간 거래 (증빙 없음) |"""

        if needs_preparation:
            markdown += "\n\n**준비 필요 항목**:\n"
            for i, tx in enumerate(needs_preparation[:10], 1):
                ctx = contexts.get(tx.id)
                memo = ctx.user_memo if ctx else tx.bank_memo
                markdown += f"{i}. {tx.date.strftime('%m월 %d일')} - {tx.counterparty or '알 수 없음'} ({tx.amount:,}원) - {memo or '메모 없음'}\n"

        return {
            "markdown": markdown,
            "ready": ready,
            "needs_preparation": needs_preparation,
            "not_available": not_available,
        }

    def _generate_recurring_section(
        self,
        transactions: list[Transaction],
        contexts: dict[str, EnrichedContext],
    ) -> str:
        """Generate recurring transactions section."""
        # Group by counterparty
        by_counterparty: dict[str, list[Transaction]] = {}
        for tx in transactions:
            key = tx.counterparty or "기타"
            if key not in by_counterparty:
                by_counterparty[key] = []
            by_counterparty[key].append(tx)

        markdown = "## 🔄 정기 지출\n"

        for counterparty, txs in by_counterparty.items():
            ctx = contexts.get(txs[0].id)
            category = ctx.category if ctx else "미분류"
            account_class = ctx.account_classification if ctx else ""
            tax_notes = ctx.tax_notes if ctx else ""
            summary = ctx.ai_generated_summary if ctx else ""

            # Get document status
            doc_status = "⚠️ 확인 필요"
            if ctx and ctx.documents:
                doc_status = ctx.documents.get("status", "⚠️ 확인 필요")

            total = sum(tx.amount for tx in txs)

            markdown += f"""
### [{counterparty}]

**거래 내역**:
"""
            for tx in txs[:5]:  # Show max 5
                markdown += f"- {tx.date.strftime('%m월 %d일')}: {tx.amount:,}원 ({tx.bank_name})\n"

            if len(txs) > 5:
                markdown += f"- ... 외 {len(txs) - 5}건\n"

            markdown += f"""
**총 금액**: {total:,}원 ({len(txs)}건)

**카테고리**: {category}
"""
            if account_class:
                markdown += f"**계정 분류**: {account_class}\n"
            if tax_notes:
                markdown += f"**세무 처리**: {tax_notes}\n"
            if summary:
                markdown += f"**설명**: {summary}\n"

            markdown += f"**증빙**: {doc_status}\n"
            markdown += "\n---\n"

        return markdown

    async def _generate_non_recurring_section(
        self,
        transactions: list[Transaction],
        contexts: dict[str, EnrichedContext],
    ) -> str:
        """Generate non-recurring transactions section with relationship grouping."""
        markdown = "## ⚡ 비정기 지출\n"

        # Group by related transactions
        grouped: list[list[Transaction]] = []
        ungrouped: list[Transaction] = []
        processed_ids: set[str] = set()

        for tx in transactions:
            if tx.id in processed_ids:
                continue

            ctx = contexts.get(tx.id)
            related_ids = ctx.related_transaction_ids if ctx else []

            if related_ids:
                # Find all related transactions
                group = [tx]
                processed_ids.add(tx.id)

                for related_id in related_ids:
                    for other_tx in transactions:
                        if other_tx.id == related_id and other_tx.id not in processed_ids:
                            group.append(other_tx)
                            processed_ids.add(other_tx.id)

                if len(group) > 1:
                    grouped.append(group)
                else:
                    ungrouped.append(tx)
            else:
                ungrouped.append(tx)
                processed_ids.add(tx.id)

        # Generate grouped sections
        for i, group in enumerate(grouped, 1):
            total = sum(tx.amount for tx in group)
            relationship = await self.ai_service.generate_transaction_relationship(
                [{"date": tx.date.strftime("%Y-%m-%d"), "counterparty": tx.counterparty, "amount": tx.amount}
                 for tx in group]
            )

            markdown += f"""
### [그룹 {i}: 관련 거래]

**거래 관계**:
{relationship}

**거래 내역**:
"""
            for tx in group:
                ctx = contexts.get(tx.id)
                memo = ctx.user_memo if ctx else tx.bank_memo
                markdown += f"- {tx.date.strftime('%m월 %d일')}: {tx.amount:,}원 - {tx.counterparty or '알 수 없음'} ({tx.bank_name})\n"
                if memo:
                    markdown += f"  메모: {memo}\n"

            markdown += f"\n**총 금액**: {total:,}원 ({len(group)}건)\n\n---\n"

        # Generate ungrouped section
        if ungrouped:
            markdown += "\n### [개별 거래]\n\n"
            for tx in ungrouped:
                ctx = contexts.get(tx.id)
                category = ctx.category if ctx else "미분류"
                summary = ctx.ai_generated_summary if ctx else ""
                doc_status = "⚠️"
                if ctx and ctx.documents:
                    doc_status = "✅" if ctx.documents.get("invoice_received") else "⚠️"

                markdown += f"- {tx.date.strftime('%m월 %d일')}: {tx.amount:,}원 - {tx.counterparty or '알 수 없음'}"
                markdown += f" [{category}] {doc_status}\n"
                if summary:
                    markdown += f"  → {summary}\n"

        return markdown

    def _generate_pending_section(self, transactions: list[Transaction]) -> str:
        """Generate pending transactions section."""
        markdown = "## ⚠️ 확인 필요 (미답변 거래)\n\n"

        for tx in transactions:
            markdown += f"- {tx.date.strftime('%m월 %d일')}: {tx.amount:,}원"
            markdown += f" ({tx.counterparty or '거래처 불명'})\n"
            markdown += f"  상태: 맥락 정보 없음, 수동 확인 필요\n"

        return markdown
