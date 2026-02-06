"""
AI service for generating smart questions and summaries.

Uses Claude API (Anthropic) with tax law context for accurate questions.
Includes hallucination prevention techniques.
"""

import json
from typing import Any, Optional

from src.config import get_settings


# System prompt for hallucination prevention
SYSTEM_PROMPT = """당신은 한국 세무/회계 전문 AI 어시스턴트입니다.

핵심 원칙:
1. 제공된 컨텍스트 내 정보만 참조하세요
2. 확신이 없으면 "세무사 확인 필요"라고 응답하세요
3. 수치는 직접 계산하고, 추측하지 마세요
4. 모든 응답에 신뢰도(confidence)를 포함하세요

응답 형식:
- 항상 JSON 형식으로 응답하세요
- questions 배열에 질문들을 포함하세요
- 각 질문에는 id, text, options, type 필드가 필요합니다"""


# Question templates for common transaction types
QUESTION_TEMPLATES = {
    "expense": [
        {
            "id": "Q1",
            "text": "이 지출의 주요 목적은 무엇인가요?",
            "options": ["사업운영", "개발/연구", "마케팅", "인건비", "기타"],
            "type": "single_choice",
        },
        {
            "id": "Q2",
            "text": "정기적으로 발생하는 지출인가요?",
            "options": ["네, 매월 반복", "네, 매주 반복", "아니오, 일회성", "불규칙"],
            "type": "single_choice",
        },
        {
            "id": "Q3",
            "text": "다른 거래와 관련이 있나요?",
            "options": ["별개 거래", "관련 있음 (직접 입력)", "모르겠음"],
            "type": "single_choice",
        },
        {
            "id": "Q4",
            "text": "📎 계산서/영수증을 받으셨나요?",
            "options": ["네, 받았어요", "아니오", "요청 예정"],
            "type": "single_choice",
        },
        {
            "id": "Q5",
            "text": "📤 증빙 서류를 업로드하시겠어요?",
            "options": ["파일 업로드", "나중에", "증빙 없음"],
            "type": "file_upload",
        },
    ],
    "income": [
        {
            "id": "Q1",
            "text": "이 입금의 출처는 무엇인가요?",
            "options": ["매출 (서비스/제품)", "투자금", "대출", "환불", "기타"],
            "type": "single_choice",
        },
        {
            "id": "Q2",
            "text": "세금계산서 발행이 필요한가요?",
            "options": ["이미 발행함", "발행 예정", "발행 불필요", "확인 필요"],
            "type": "single_choice",
        },
    ],
}

# Category-specific questions
CATEGORY_QUESTIONS = {
    "AWS": [
        {
            "id": "Q_AWS",
            "text": "AWS 비용의 주 용도는?",
            "options": ["개발 서버", "프로덕션 서버", "데이터 저장", "AI/ML 서비스"],
            "type": "single_choice",
        },
    ],
    "급여": [
        {
            "id": "Q_SALARY",
            "text": "이 급여 지급 대상은?",
            "options": ["정규직", "계약직", "프리랜서", "아르바이트"],
            "type": "single_choice",
        },
    ],
    "마케팅": [
        {
            "id": "Q_MARKETING",
            "text": "마케팅 유형은?",
            "options": ["온라인 광고", "오프라인 광고", "이벤트/프로모션", "콘텐츠 제작"],
            "type": "single_choice",
        },
    ],
}


class AIService:
    """
    AI service for generating tax-aware smart questions and summaries.

    Uses Claude API when configured, falls back to template-based questions
    when API is not available.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.is_mock = not self.api_key

        if not self.is_mock:
            try:
                from anthropic import AsyncAnthropic

                self.client = AsyncAnthropic(api_key=self.api_key)
                self.model = "claude-3-5-sonnet-20241022"
            except ImportError:
                self.is_mock = True
                self.client = None
        else:
            self.client = None

    async def generate_smart_questions(
        self,
        transaction: dict,
        past_patterns: Optional[list[dict]] = None,
        tax_context: Optional[dict] = None,
    ) -> dict:
        """
        Generate smart questions for a transaction.

        Args:
            transaction: Transaction data
            past_patterns: Similar past transactions
            tax_context: Relevant tax law context

        Returns:
            Dictionary with questions and metadata
        """
        if self.is_mock:
            return self._generate_template_questions(transaction, past_patterns)

        # Build prompt for Claude
        prompt = self._build_question_prompt(transaction, past_patterns, tax_context)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic for consistency
            )

            # Parse response
            content = response.content[0].text
            return self._parse_ai_response(content, transaction)

        except Exception as e:
            # Fallback to templates on error
            print(f"AI API error: {e}")
            return self._generate_template_questions(transaction, past_patterns)

    def _build_question_prompt(
        self,
        transaction: dict,
        past_patterns: Optional[list[dict]],
        tax_context: Optional[dict],
    ) -> str:
        """Build prompt for AI question generation."""
        prompt = f"""거래 정보를 분석하고 세무사가 필요로 할 맥락 정보를 수집하기 위한 질문을 생성해주세요.

## 거래 정보
- 날짜: {transaction.get('date', '')}
- 시간: {transaction.get('time', '')}
- 금액: {transaction.get('amount', 0):,}원
- 유형: {transaction.get('type', '')}
- 거래처: {transaction.get('counterparty', '알 수 없음')}
- 은행 메모: {transaction.get('bank_memo', '')}
- 은행: {transaction.get('bank_name', '')}
"""

        if past_patterns:
            prompt += "\n## 과거 유사 거래\n"
            for p in past_patterns[:3]:
                prompt += f"- {p.get('date')}: {p.get('counterparty')} {p.get('amount'):,}원\n"

        if tax_context:
            prompt += f"\n## 관련 세법 컨텍스트\n{tax_context.get('summary', '')}\n"

        prompt += """
## 요청사항
1. 세무사가 이 거래를 이해하는 데 필요한 질문 3-5개를 생성해주세요
2. 각 질문은 객관식(2-4개 옵션)으로 만들어주세요
3. 증빙 서류 관련 질문을 반드시 포함해주세요
4. JSON 형식으로 응답해주세요

응답 형식:
{
  "questions": [
    {"id": "Q1", "text": "질문 내용", "options": ["옵션1", "옵션2"], "type": "single_choice"},
    ...
  ],
  "confidence": 0.9,
  "category_suggestion": "추천 카테고리"
}"""

        return prompt

    def _parse_ai_response(self, content: str, transaction: dict) -> dict:
        """Parse AI response and validate."""
        try:
            # Try to extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)

                # Validate questions
                questions = data.get("questions", [])
                valid_questions = []
                for q in questions:
                    if all(k in q for k in ["id", "text", "options", "type"]):
                        valid_questions.append(q)

                return {
                    "questions": valid_questions,
                    "confidence": data.get("confidence", 0.8),
                    "category_suggestion": data.get("category_suggestion"),
                    "source": "ai",
                }
        except json.JSONDecodeError:
            pass

        # Fallback to templates if parsing fails
        return self._generate_template_questions(transaction, None)

    def _generate_template_questions(
        self,
        transaction: dict,
        past_patterns: Optional[list[dict]],
    ) -> dict:
        """Generate questions using templates (fallback/mock mode)."""
        tx_type = transaction.get("type", "지출")
        counterparty = transaction.get("counterparty", "").upper()

        # Base questions based on type
        if tx_type == "입금":
            questions = QUESTION_TEMPLATES["income"].copy()
        else:
            questions = QUESTION_TEMPLATES["expense"].copy()

        # Add category-specific questions
        for keyword, cat_questions in CATEGORY_QUESTIONS.items():
            if keyword.upper() in counterparty:
                questions.extend(cat_questions)
                break

        # Customize based on patterns
        if past_patterns and len(past_patterns) > 2:
            # Likely recurring - adjust question
            for q in questions:
                if q["id"] == "Q2":
                    q["options"][0] = f"네, 매월 반복 (이전 {len(past_patterns)}건 확인)"

        return {
            "questions": questions[:7],  # Max 7 questions
            "confidence": 0.7,
            "category_suggestion": self._suggest_category(transaction),
            "source": "template",
        }

    def _suggest_category(self, transaction: dict) -> str:
        """Suggest category based on transaction data."""
        counterparty = transaction.get("counterparty", "").lower()
        memo = transaction.get("bank_memo", "").lower()

        keywords = {
            "개발비 - 클라우드": ["aws", "azure", "gcp", "네이버클라우드", "서버"],
            "인건비 - 급여": ["급여", "월급", "salary"],
            "마케팅비": ["광고", "마케팅", "marketing", "ad"],
            "임차료": ["월세", "임대", "사무실"],
            "통신비": ["통신", "인터넷", "kt", "skt", "lg"],
            "소모품비": ["사무용품", "소모품", "문구"],
            "식대": ["식대", "점심", "저녁", "식사"],
        }

        combined = f"{counterparty} {memo}"
        for category, kws in keywords.items():
            if any(kw in combined for kw in kws):
                return category

        return "기타 경비"

    async def generate_ai_summary(
        self,
        transaction: dict,
        answers: list[dict],
    ) -> dict:
        """
        Generate AI summary for tax accountant.

        Args:
            transaction: Transaction data
            answers: User answers to questions

        Returns:
            Dictionary with summary and metadata
        """
        if self.is_mock:
            return self._generate_template_summary(transaction, answers)

        prompt = f"""거래 정보와 유저 답변을 바탕으로 세무사에게 전달할 요약을 작성해주세요.

## 거래 정보
- 날짜: {transaction.get('date', '')}
- 금액: {transaction.get('amount', 0):,}원
- 유형: {transaction.get('type', '')}
- 거래처: {transaction.get('counterparty', '')}
- 은행 메모: {transaction.get('bank_memo', '')}

## 유저 답변
{json.dumps(answers, ensure_ascii=False, indent=2)}

## 요청사항
세무사가 이해할 수 있는 2-3문장 요약을 작성해주세요.
계정 분류, 세무 처리 관련 메모도 포함해주세요.

응답 형식:
{{
  "summary": "요약 내용",
  "account_classification": "계정 분류",
  "tax_notes": "세무 처리 메모"
}}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )

            content = response.content[0].text
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])

        except Exception as e:
            print(f"AI summary error: {e}")

        return self._generate_template_summary(transaction, answers)

    def _generate_template_summary(
        self,
        transaction: dict,
        answers: list[dict],
    ) -> dict:
        """Generate template-based summary (fallback)."""
        counterparty = transaction.get("counterparty", "알 수 없음")
        amount = transaction.get("amount", 0)
        memo = transaction.get("bank_memo", "")
        category = self._suggest_category(transaction)

        # Extract key answers
        purpose = next((a["answer"] for a in answers if a.get("question_id") == "Q1"), "")
        recurring = next((a["answer"] for a in answers if a.get("question_id") == "Q2"), "")

        summary = f"{counterparty} {amount:,}원"
        if memo:
            summary += f", {memo}"
        if purpose:
            summary += f". 용도: {purpose}"
        if "매월" in recurring or "매주" in recurring:
            summary += " (정기 지출)"

        return {
            "summary": summary,
            "account_classification": category,
            "tax_notes": "세무사 확인 권장" if not purpose else "",
        }

    async def generate_transaction_relationship(
        self,
        transactions: list[dict],
    ) -> str:
        """
        Generate explanation of relationship between transactions.

        Args:
            transactions: Related transactions

        Returns:
            Relationship explanation text
        """
        if len(transactions) < 2:
            return ""

        if self.is_mock:
            # Simple template-based relationship
            total = sum(tx.get("amount", 0) for tx in transactions)
            return (
                f"위 {len(transactions)}건의 거래는 관련된 일련의 지출입니다. "
                f"총 금액: {total:,}원"
            )

        # AI-based relationship analysis
        tx_list = "\n".join(
            f"- {tx.get('date')}: {tx.get('counterparty')} {tx.get('amount', 0):,}원"
            for tx in transactions
        )

        prompt = f"""다음 거래들의 관계를 2-3문장으로 설명해주세요.

{tx_list}

세무사가 이해할 수 있도록 비즈니스 맥락을 포함해주세요."""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Relationship generation error: {e}")
            total = sum(tx.get("amount", 0) for tx in transactions)
            return f"관련 거래 {len(transactions)}건, 총 {total:,}원"
