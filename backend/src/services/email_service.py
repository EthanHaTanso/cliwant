"""
Email service for sending documents to accountant.

Supports real SMTP and mock mode for development.
"""

from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from src.config import get_settings


class EmailService:
    """
    Email service for accountant delivery.

    When SMTP is not configured, uses mock implementation
    that logs emails instead of sending them.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: Optional[str] = None,
    ):
        settings = get_settings()
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.user = user or settings.smtp_user
        self.password = password or settings.smtp_password
        self.from_addr = from_addr or settings.smtp_from

        self.is_mock = not all([self.host, self.user, self.password])

    async def send_to_accountant(
        self,
        to_email: str,
        user_name: str,
        month: str,
        total_transactions: int,
        total_income: int,
        total_expense: int,
        attachment_content: bytes,
        attachment_filename: str,
    ) -> dict:
        """
        Send monthly document to accountant via email.

        Args:
            to_email: Accountant's email address
            user_name: User's name for greeting
            month: Month string (e.g., "2026-02")
            total_transactions: Total transaction count
            total_income: Total income amount
            total_expense: Total expense amount
            attachment_content: Excel file content as bytes
            attachment_filename: Attachment filename

        Returns:
            Dictionary with status and details
        """
        # Build email
        subject = f"[{user_name}] {month} 부가세 신고 자료"

        body = f"""안녕하세요,

{month} 입출금 내역을 첨부합니다.

- 총 거래 건수: {total_transactions}건
- 총 입금: {total_income:,}원
- 총 지출: {total_expense:,}원

상세 내역은 첨부 파일을 확인해주세요.
별도 문의사항 있으시면 연락 부탁드립니다.

감사합니다.

---
[AI Tax Assistant 자동 생성 메시지]
"""

        if self.is_mock:
            return await self._mock_send(
                to_email=to_email,
                subject=subject,
                body=body,
                attachment_filename=attachment_filename,
            )

        # Real SMTP send
        try:
            import aiosmtplib

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = to_email
            msg["Subject"] = subject

            # Body
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Attachment
            attachment = MIMEApplication(attachment_content, Name=attachment_filename)
            attachment["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(attachment)

            # Send
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
            )

            return {
                "status": "sent",
                "to": to_email,
                "sent_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "to": to_email,
            }

    async def _mock_send(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_filename: str,
    ) -> dict:
        """Mock send - logs email instead of sending."""
        print(f"\n{'='*60}")
        print(f"📧 MOCK EMAIL")
        print(f"{'='*60}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"{'─'*40}")
        print(body)
        print(f"{'─'*40}")
        print(f"Attachment: {attachment_filename}")
        print(f"{'='*60}\n")

        return {
            "status": "mock_sent",
            "to": to_email,
            "sent_at": datetime.utcnow().isoformat(),
        }
