"""
Slack service for sending notifications and handling interactions.

Supports real Slack API and mock mode for development.
"""

import json
from datetime import datetime
from typing import Any, Optional

from src.config import get_settings


class SlackService:
    """
    Slack API service for notifications and interactive messages.

    When Slack credentials are not configured, uses mock implementation
    that logs messages instead of sending them.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        settings = get_settings()
        self.bot_token = bot_token or settings.slack_bot_token
        self.channel_id = channel_id or settings.slack_channel_id
        self.is_mock = not (self.bot_token and self.channel_id)

        if not self.is_mock:
            try:
                from slack_sdk import WebClient

                self.client = WebClient(token=self.bot_token)
            except ImportError:
                self.is_mock = True
                self.client = None
        else:
            self.client = None

    async def send_daily_questions(
        self,
        transactions: list[dict],
        questions_by_transaction: dict[str, list[dict]],
    ) -> dict:
        """
        Send daily questions for pending transactions.

        Args:
            transactions: List of transactions needing enrichment
            questions_by_transaction: Questions mapped by transaction ID

        Returns:
            Response with status and message details
        """
        if not transactions:
            return {"status": "skipped", "reason": "no_transactions"}

        # Build Slack blocks
        blocks = self._build_question_blocks(transactions, questions_by_transaction)

        if self.is_mock:
            return await self._mock_send(blocks, "daily_questions")

        # Real Slack API call
        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
                text=f"어제 거래 {len(transactions)}건 확인 필요",
            )
            return {
                "status": "sent",
                "ts": response["ts"],
                "channel": response["channel"],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _build_question_blocks(
        self,
        transactions: list[dict],
        questions_by_transaction: dict[str, list[dict]],
    ) -> list[dict]:
        """Build Slack Block Kit blocks for questions."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *어제 거래 {len(transactions)}건 확인 필요* (예상 소요: {len(transactions)}분)",
                },
            },
            {"type": "divider"},
        ]

        for i, tx in enumerate(transactions, 1):
            # Transaction header
            amount_formatted = f"{tx['amount']:,}원"
            tx_type = tx.get("type", "지출")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{i}️⃣ *{tx.get('date', '')} {tx.get('time', '')[:5]}*\n"
                            f"   {tx.get('counterparty', '알 수 없음')} "
                            f"{amount_formatted} {tx_type} ({tx.get('bank_name', '')})\n"
                            f"   📝 메모: {tx.get('bank_memo', '-')}"
                        ),
                    },
                }
            )

            # Questions for this transaction
            questions = questions_by_transaction.get(tx["id"], [])
            for q in questions:
                # Create button elements for options
                elements = []
                for opt in q.get("options", [])[:5]:  # Max 5 buttons per row
                    elements.append(
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": opt[:20]},  # Max 20 chars
                            "action_id": f"answer_{tx['id']}_{q['id']}_{opt[:20]}",
                            "value": json.dumps(
                                {
                                    "tx_id": tx["id"],
                                    "q_id": q["id"],
                                    "answer": opt,
                                }
                            ),
                        }
                    )

                if elements:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"💬 {q.get('text', '')}",
                            },
                        }
                    )
                    blocks.append(
                        {
                            "type": "actions",
                            "block_id": f"q_{tx['id']}_{q['id']}",
                            "elements": elements,
                        }
                    )

            blocks.append({"type": "divider"})

        return blocks

    async def send_reminder(
        self,
        transaction_id: str,
        transaction_summary: str,
        hours_since: int,
    ) -> dict:
        """
        Send reminder for unanswered questions.

        Args:
            transaction_id: Transaction ID
            transaction_summary: Brief description
            hours_since: Hours since original question

        Returns:
            Response with status
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"⏰ *리마인더*: 아직 답변하지 않은 거래가 있습니다\n\n"
                        f"• {transaction_summary}\n"
                        f"• {hours_since}시간 전 질문 발송됨"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "답변하러 가기 →"},
                        "url": f"http://localhost:3000/transactions/{transaction_id}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "나중에 답변"},
                        "action_id": f"skip_{transaction_id}",
                    },
                ],
            },
        ]

        if self.is_mock:
            return await self._mock_send(blocks, "reminder")

        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
                text=f"리마인더: {transaction_summary}",
            )
            return {"status": "sent", "ts": response["ts"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def send_document_ready(
        self,
        document_id: str,
        summary: dict,
    ) -> dict:
        """
        Send notification when monthly document is ready.

        Args:
            document_id: Document ID
            summary: Document summary stats

        Returns:
            Response with status
        """
        month = summary.get("month", "")
        total = summary.get("total_transactions", 0)
        recurring = summary.get("recurring_count", 0)
        non_recurring = summary.get("non_recurring_count", 0)
        pending = summary.get("pending_count", 0)

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📄 *{month} 부가세 신고 문서 준비 완료!*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"총 *{total}건* 거래 정리됨\n"
                        f"• 정기 지출: {recurring}건 (자동 분류)\n"
                        f"• 비정기 지출: {non_recurring}건 (상세 맥락 포함)\n"
                        f"• 확인 필요: {pending}건"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "문서 확인하기 →"},
                        "url": f"http://localhost:3000/documents/{document_id}",
                        "style": "primary",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "예상 소요 시간: 10분"},
                ],
            },
        ]

        if self.is_mock:
            return await self._mock_send(blocks, "document_ready")

        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
                text=f"{month} 부가세 신고 문서 준비 완료!",
            )
            return {"status": "sent", "ts": response["ts"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def handle_button_click(self, payload: dict) -> dict:
        """
        Handle Slack interactive button click.

        Args:
            payload: Slack interaction payload

        Returns:
            Parsed answer data
        """
        action = payload.get("actions", [{}])[0]
        value = action.get("value", "{}")

        try:
            data = json.loads(value)
            return {
                "status": "success",
                "transaction_id": data.get("tx_id"),
                "question_id": data.get("q_id"),
                "answer": data.get("answer"),
                "user_id": payload.get("user", {}).get("id"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except json.JSONDecodeError:
            # Fallback: parse from action_id
            action_id = action.get("action_id", "")
            parts = action_id.split("_")
            if len(parts) >= 4 and parts[0] == "answer":
                return {
                    "status": "success",
                    "transaction_id": parts[1],
                    "question_id": parts[2],
                    "answer": "_".join(parts[3:]),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return {"status": "error", "error": "Could not parse interaction"}

    async def _mock_send(self, blocks: list[dict], message_type: str) -> dict:
        """Mock send - logs message instead of sending to Slack."""
        print(f"\n{'='*60}")
        print(f"🔔 MOCK SLACK MESSAGE ({message_type})")
        print(f"{'='*60}")
        for block in blocks:
            if block.get("type") == "section":
                text = block.get("text", {}).get("text", "")
                print(f"  {text}")
            elif block.get("type") == "actions":
                buttons = [
                    e.get("text", {}).get("text", "")
                    for e in block.get("elements", [])
                    if e.get("type") == "button"
                ]
                print(f"  [Buttons: {', '.join(buttons)}]")
            elif block.get("type") == "divider":
                print(f"  {'─'*40}")
        print(f"{'='*60}\n")

        return {
            "status": "mock_sent",
            "message_type": message_type,
            "blocks_count": len(blocks),
        }
