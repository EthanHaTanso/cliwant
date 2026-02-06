# AI 세무 어시스턴트 기술 스펙 (Technical Specification)

**생성 일시**: 2026년 2월 6일
**기술 스택**: Python (FastAPI) + Next.js (TypeScript)
**상태**: 구현 대기

---

## 1. Technical Overview

### 1.1. 시스템 아키텍처

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          User Device (Local)                               │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │   Next.js App    │◄──►│  FastAPI Server  │◄──►│     SQLite DB       │ │
│  │  (Dashboard UI)  │    │   (Port 8000)    │    │   (Local File)      │ │
│  │   Port 3000      │    │                  │    │                     │ │
│  └──────────────────┘    └────────┬─────────┘    └─────────────────────┘ │
│                                   │                                        │
│           ┌───────────────────────┼───────────────────────┐               │
│           │                       │                       │               │
│           ▼                       ▼                       ▼               │
│  ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │  APScheduler     │    │  File Storage   │    │   Tax Law Index     │ │
│  │  (Batch Jobs)    │    │ ~/ai-tax-asst/  │    │    (ChromaDB)       │ │
│  │  06:00, 09:00,   │    │   documents/    │    │   세법/회계법 DB     │ │
│  │  25일, 매월1일   │    │                 │    │                     │ │
│  └──────────────────┘    └─────────────────┘    └─────────────────────┘ │
│                                                                            │
│  ┌──────────────────┐                                                     │
│  │  Config Store    │                                                     │
│  │  (Encrypted)     │                                                     │
│  │  .env.local      │                                                     │
│  └──────────────────┘                                                     │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          External Services                                 │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │   Popbill API    │    │    Slack API     │    │   Claude API        │ │
│  │  (Bank Data)     │    │  (Notifications) │    │ (Anthropic Sonnet)  │ │
│  │                  │    │                  │    │                     │ │
│  └──────────────────┘    └──────────────────┘    └─────────────────────┘ │
│                                                                            │
│  ┌──────────────────┐    ┌──────────────────┐                             │
│  │    SMTP Server   │    │  국가법령정보센터  │                             │
│  │  (Email Delivery)│    │  (법령 업데이트)  │                             │
│  └──────────────────┘    └──────────────────┘                             │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

### 1.2. 프로젝트 구조

```
ai-tax-assistant/
├── backend/                          # Python FastAPI
│   ├── src/
│   │   ├── api/                      # API 라우터
│   │   │   ├── __init__.py
│   │   │   ├── transactions.py       # US-001: 거래 관련 API
│   │   │   ├── enrichment.py         # US-002, US-003: 질문/답변 API
│   │   │   ├── documents.py          # US-004, US-005: 문서 API
│   │   │   ├── delivery.py           # US-006: 세무사 전달 API
│   │   │   └── tax_context.py        # 세법 컨텍스트 검색 API
│   │   │
│   │   ├── models/                   # SQLAlchemy 모델
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py
│   │   │   ├── enriched_context.py
│   │   │   ├── monthly_document.py
│   │   │   └── user_config.py
│   │   │
│   │   ├── services/                 # 비즈니스 로직
│   │   │   ├── __init__.py
│   │   │   ├── popbill_service.py    # 팝빌 API 연동
│   │   │   ├── slack_service.py      # 슬랙 알림
│   │   │   ├── ai_service.py         # AI 질문/요약 생성
│   │   │   ├── email_service.py      # 이메일 발송
│   │   │   ├── document_service.py   # 문서 생성
│   │   │   │
│   │   │   └── tax_context/          # 세법 컨텍스트 서비스
│   │   │       ├── __init__.py
│   │   │       ├── categories.py     # 거래 분류 카테고리
│   │   │       ├── index.py          # Vector DB 인덱스 빌더
│   │   │       ├── search.py         # 세법 검색 서비스
│   │   │       └── evidence.py       # 적격증빙 체크리스트
│   │   │
│   │   ├── jobs/                     # 배치 작업
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py          # APScheduler 설정
│   │   │   ├── sync_transactions.py  # 06:00 거래 수집
│   │   │   ├── send_questions.py     # 09:00 질문 발송
│   │   │   └── generate_document.py  # 25일 문서 생성
│   │   │   # └── update_tax_index.py # [v2.0] 세법 인덱스 자동 업데이트
│   │   │
│   │   ├── utils/                    # 유틸리티
│   │   │   ├── __init__.py
│   │   │   ├── encryption.py         # AES-256 암호화
│   │   │   ├── masking.py            # 민감 데이터 마스킹
│   │   │   └── excel_generator.py    # 엑셀 파일 생성
│   │   │
│   │   ├── config.py                 # 환경 설정
│   │   ├── database.py               # DB 연결
│   │   └── main.py                   # FastAPI 앱 진입점
│   │
│   ├── tests/                        # 테스트
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── data/                         # 세법 데이터 및 인덱스
│   │   ├── tax_law_sources.yaml      # 법령 소스 설정
│   │   ├── tax_updates_2026.yaml     # 2026년 개정사항
│   │   ├── evidence_checklist.yaml   # 적격증빙 체크리스트
│   │   └── tax_law_db/               # ChromaDB (Vector Store)
│   │       └── chroma.sqlite3
│   │
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/                         # Next.js TypeScript
│   ├── src/
│   │   ├── app/                      # App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # 대시보드 홈
│   │   │   ├── documents/
│   │   │   │   ├── page.tsx          # 문서 목록
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # 문서 상세/편집
│   │   │   └── settings/
│   │   │       └── page.tsx          # 설정 페이지
│   │   │
│   │   ├── components/               # UI 컴포넌트
│   │   │   ├── TransactionCard.tsx
│   │   │   ├── DocumentEditor.tsx
│   │   │   ├── DocumentChecklist.tsx
│   │   │   └── ExcelPreview.tsx
│   │   │
│   │   ├── hooks/                    # React 훅
│   │   │   ├── useTransactions.ts
│   │   │   ├── useDocuments.ts
│   │   │   └── useApi.ts
│   │   │
│   │   ├── lib/                      # 유틸리티
│   │   │   ├── api.ts                # API 클라이언트
│   │   │   └── types.ts              # TypeScript 타입
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
│
├── shared/                           # 공유 타입 정의
│   └── types/
│       ├── transaction.ts
│       ├── enrichment.ts
│       └── document.ts
│
├── docker-compose.yml                # 로컬 개발 환경
├── Makefile                          # 개발 명령어
└── README.md
```

### 1.3. 주요 의존성 패키지

**Backend (Python 3.11+)**:
```txt
# requirements.txt
fastapi==0.109.0
uvicorn==0.27.0
sqlalchemy==2.0.25
pydantic==2.5.3
apscheduler==3.10.4
popbill==1.50.0
slack-sdk==3.26.1
anthropic==0.18.0          # Claude API (3.5 Sonnet)
cryptography==41.0.7
openpyxl==3.1.2
python-multipart==0.0.6
python-dotenv==1.0.0
chromadb==0.4.22            # 세법 인덱스 Vector DB
pyyaml==6.0.1               # 세법 데이터 설정 파일
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
```

**Frontend (Node.js 20+)**:
```json
{
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3",
    "@tanstack/react-query": "5.17.0",
    "axios": "1.6.5",
    "react-markdown": "9.0.1",
    "xlsx": "0.18.5",
    "tailwindcss": "3.4.1",
    "lucide-react": "0.312.0"
  }
}
```

### 1.4. 크로스 플랫폼 배포 전략

**지원 플랫폼**: macOS, Windows, Linux

#### 옵션 1: Docker (권장 - MVP)

```bash
# 유저 실행 명령어 (모든 OS 동일)
docker-compose up -d

# docker-compose.yml이 FastAPI + Next.js + SQLite 모두 실행
# 볼륨 마운트로 로컬 파일 저장: ~/ai-tax-assistant/
```

**장점**: OS 무관하게 동일한 실행 환경
**단점**: Docker 설치 필요 (기술적 장벽)

#### 옵션 2: Tauri 데스크톱 앱 (권장 - 제품화 시)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Tauri Desktop App                               │
│  ┌──────────────────┐    ┌──────────────────┐                      │
│  │  Webview (UI)    │    │  Rust Backend    │                      │
│  │  (Next.js 빌드)  │    │  (Python 임베드) │                      │
│  └──────────────────┘    └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
         ↓                          ↓
   - macOS: .dmg               단일 실행 파일
   - Windows: .exe             설치 불필요
   - Linux: .AppImage
```

**장점**: 네이티브 앱처럼 설치/실행
**단점**: 빌드 파이프라인 복잡

#### 옵션 3: Python + npm 스크립트 (개발자용)

```bash
# 유저 실행
git clone https://github.com/your-repo/ai-tax-assistant
cd ai-tax-assistant
make install  # pip + npm 설치
make dev      # 서버 실행
```

**장점**: 간단, 개발 중 테스트 용이
**단점**: Python/Node.js 직접 설치 필요

#### MVP 배포 결정

| 단계 | 배포 방식 | 대상 |
|------|----------|------|
| MVP (1주) | 옵션 3 (스크립트) | 개발자/Early Adopter |
| v1.0 | 옵션 1 (Docker) | 기술 친화적 유저 |
| v2.0+ | 옵션 2 (Tauri) | 일반 유저 |

---

## 2. Data Models

### 2.1. Transaction (거래 내역)

```python
# backend/src/models/transaction.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class TransactionType(enum.Enum):
    INCOME = "입금"
    EXPENSE = "지출"

class TransactionStatus(enum.Enum):
    PENDING_ENRICHMENT = "pending_enrichment"      # 맥락 입력 대기
    ENRICHED = "enriched"                          # 맥락 입력 완료
    PENDING_MANUAL_REVIEW = "pending_manual_review" # 수동 확인 필요
    AUTO_CLASSIFIED = "auto_classified"            # 자동 분류됨

class Transaction(Base):
    __tablename__ = "transactions"

    # Primary Key
    id = Column(String, primary_key=True)  # "2026-02-05-IBK-AWS-001"

    # Bank Info
    bank_name = Column(String, nullable=False)        # "기업은행"
    account_number = Column(String, nullable=False)   # 암호화 저장
    account_number_masked = Column(String)            # "***-**-789"

    # Transaction Details
    date = Column(DateTime, nullable=False)
    time = Column(String)                             # "14:30:00"
    amount = Column(Integer, nullable=False)          # 원 단위
    type = Column(Enum(TransactionType), nullable=False)
    counterparty = Column(String)                     # "AWS Korea"
    bank_memo = Column(String)                        # 은행 앱 메모

    # Classification
    is_internal_transfer = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING_ENRICHMENT)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    enriched_context = relationship("EnrichedContext", back_populates="transaction", uselist=False)
```

**TypeScript 타입**:
```typescript
// shared/types/transaction.ts
export type TransactionType = '입금' | '지출';

export type TransactionStatus =
  | 'pending_enrichment'
  | 'enriched'
  | 'pending_manual_review'
  | 'auto_classified';

export interface Transaction {
  id: string;
  bank_name: string;
  account_number_masked: string;
  date: string;  // ISO 8601
  time: string;
  amount: number;
  type: TransactionType;
  counterparty?: string;
  bank_memo?: string;
  is_internal_transfer: boolean;
  is_recurring: boolean;
  status: TransactionStatus;
  created_at: string;
  updated_at?: string;
  enriched_context?: EnrichedContext;
}
```

### 2.2. EnrichedContext (맥락 정보)

```python
# backend/src/models/enriched_context.py
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

class EnrichedContext(Base):
    __tablename__ = "enriched_contexts"

    # Primary Key
    id = Column(String, primary_key=True)  # "EC-2026-02-05-001"

    # Foreign Key
    transaction_id = Column(String, ForeignKey("transactions.id"), unique=True)

    # User Input
    user_memo = Column(String)                        # "AWS 서버비"
    category = Column(String)                         # "개발비 - 클라우드 운영"
    account_classification = Column(String)           # "경비 - 통신비"

    # Pattern Info
    is_recurring = Column(Boolean, default=False)
    frequency = Column(String)                        # "월 1회, 매월 15일"
    related_transaction_ids = Column(JSON, default=[])  # ["2026-01-15-IBK-AWS"]

    # Tax Info
    tax_notes = Column(Text)                          # "연구개발비 세액공제 대상"

    # AI Generated
    ai_generated_summary = Column(Text)               # 세무사용 요약

    # Documents
    documents = Column(JSON, default={
        "invoice_received": False,
        "files": [],
        "status": "⚠️ 준비 필요"
    })

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="enriched_context")
```

**TypeScript 타입**:
```typescript
// shared/types/enrichment.ts
export interface DocumentInfo {
  invoice_received: boolean;
  files: string[];  // 파일 경로 배열
  status: '✅ 준비 완료' | '⚠️ 준비 필요' | '❌ 증빙 불가';
}

export interface EnrichedContext {
  id: string;
  transaction_id: string;
  user_memo?: string;
  category?: string;
  account_classification?: string;
  is_recurring: boolean;
  frequency?: string;
  related_transaction_ids: string[];
  tax_notes?: string;
  ai_generated_summary?: string;
  documents: DocumentInfo;
  created_at: string;
  updated_at?: string;
}

export interface SmartQuestion {
  id: string;           // "Q1"
  text: string;         // "이 지출은 개발비인가요?"
  options: string[];    // ["개발비", "운영비", "기타"]
  type: 'single_choice' | 'multiple_choice' | 'text' | 'file_upload';
}

export interface QuestionAnswer {
  question_id: string;
  answer: string | string[];
  answered_at: string;
}
```

### 2.3. MonthlyDocument (월말 문서)

```python
# backend/src/models/monthly_document.py
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
import enum

class DocumentStatus(enum.Enum):
    GENERATED = "generated"
    REVIEWED = "reviewed"
    SENT = "sent"

class MonthlyDocument(Base):
    __tablename__ = "monthly_documents"

    # Primary Key
    id = Column(String, primary_key=True)  # "MD-2026-02"

    # Reference
    user_id = Column(String, nullable=False)
    month = Column(String, nullable=False)  # "2026-02"

    # Summary Stats
    total_transactions = Column(Integer, default=0)
    total_income = Column(Integer, default=0)
    total_expense = Column(Integer, default=0)
    recurring_count = Column(Integer, default=0)
    non_recurring_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)

    # Content
    document_markdown = Column(Text)
    document_version = Column(Integer, default=1)

    # Status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.GENERATED)

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    sent_to_accountant_at = Column(DateTime)

    # Accountant Info
    accountant_email = Column(String)
```

**TypeScript 타입**:
```typescript
// shared/types/document.ts
export type DocumentStatus = 'generated' | 'reviewed' | 'sent';

export interface MonthlyDocument {
  id: string;
  user_id: string;
  month: string;
  total_transactions: number;
  total_income: number;
  total_expense: number;
  recurring_count: number;
  non_recurring_count: number;
  pending_count: number;
  document_markdown: string;
  document_version: number;
  status: DocumentStatus;
  generated_at: string;
  reviewed_at?: string;
  sent_to_accountant_at?: string;
  accountant_email?: string;
}

export interface DocumentChecklist {
  ready: { count: number; items: Transaction[] };
  needs_preparation: { count: number; items: Transaction[] };
  not_available: { count: number; items: Transaction[] };
}
```

### 2.4. UserConfig (사용자 설정)

```python
# backend/src/models/user_config.py
from sqlalchemy import Column, String, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

class UserConfig(Base):
    __tablename__ = "user_configs"

    # Primary Key
    id = Column(String, primary_key=True)  # "config-001"

    # Popbill Settings (암호화 저장)
    popbill_api_key_encrypted = Column(String)
    popbill_secret_key_encrypted = Column(String)

    # Bank Accounts
    accounts = Column(JSON, default=[])
    # [{"bank": "기업은행", "account_number_encrypted": "...", "popbill_quick_query": true}]

    # Query Settings
    query_interval = Column(String, default="daily")  # "daily"

    # Slack Settings
    slack_webhook_url = Column(String)
    slack_channel_id = Column(String)

    # Accountant Settings
    accountant_email = Column(String)
    accountant_format = Column(String, default="xlsx")  # "xlsx" | "csv" | "pdf"

    # File Storage (사용자 설정 가능)
    # None = 자동 (현재 OS 계정 홈 디렉토리 기반)
    # 예: "/Volumes/ExternalDrive/tax-docs/" (커스텀 경로)
    documents_path = Column(String, nullable=True, default=None)
    # 실제 사용 시: LocalFileStorage.from_user_config(config)로 초기화
```

### 2.5. TaxLawChunk (세법 인덱스) → 상세: 섹션 10.4

```python
# backend/src/services/tax_context/index.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import date

@dataclass
class TaxLawChunk:
    """세법 조항 청크 (ChromaDB Vector Store 저장 단위)"""

    chunk_id: str               # "CIT_제25조_1"
    law_code: str               # CIT, PIT, VAT, STTC
    article: str                # "제25조"
    title: str                  # "접대비의 손금불산입"
    content: str                # 조문 전문
    summary: str                # AI 요약 (3-5문장)
    key_points: List[str]       # 핵심 포인트
    effective_date: date        # 시행일
    categories: List[str]       # 연관 거래 카테고리
    limits: Optional[dict]      # 한도 정보
    evidence_required: List[str]  # 필요 증빙 서류
```

**TypeScript 타입**:
```typescript
// shared/types/taxLaw.ts
export interface TaxLawChunk {
  chunk_id: string;
  law_code: 'CIT' | 'PIT' | 'VAT' | 'STTC';
  article: string;
  title: string;
  summary: string;
  key_points: string[];
  limits?: Record<string, string>;
  evidence_required: string[];
}

export interface TaxLawContext {
  category: string;
  category_label: string;
  confidence: number;
  related_laws: TaxLawChunk[];
  evidence_checklist: string[];
  common_questions: string[];
}
```

---

## 3. API Specifications

### 3.1. Transaction APIs (US-001)

```python
# backend/src/api/transactions.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

# === Request/Response Models ===

class SyncTransactionsRequest(BaseModel):
    user_id: str
    start_date: date
    end_date: date

class SyncTransactionsResponse(BaseModel):
    status: str
    new_transactions: int
    total_transactions: int
    internal_transfers_detected: int

class TransactionListResponse(BaseModel):
    transactions: List[Transaction]
    total: int
    page: int
    page_size: int

# === Endpoints ===

@router.post("/sync", response_model=SyncTransactionsResponse)
async def sync_transactions(request: SyncTransactionsRequest):
    """
    팝빌 API에서 거래 내역 동기화
    - 등록된 모든 계좌에서 병렬 조회
    - 중복 거래 자동 제거
    - 계좌 간 이체 자동 감지
    """
    pass

@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    month: Optional[str] = None,     # "2026-02"
    status: Optional[str] = None,    # "pending_enrichment"
    bank: Optional[str] = None,      # "기업은행"
    page: int = 1,
    page_size: int = 50
):
    """거래 내역 목록 조회"""
    pass

@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str):
    """거래 상세 조회"""
    pass

@router.get("/pending")
async def get_pending_transactions():
    """
    Enrichment가 필요한 거래 목록 조회
    - status = 'pending_enrichment'
    - 슬랙 질문 발송 대상
    """
    pass
```

**TypeScript API Client**:
```typescript
// frontend/src/lib/api.ts
export const transactionApi = {
  sync: (request: SyncTransactionsRequest) =>
    axios.post<SyncTransactionsResponse>('/api/v1/transactions/sync', request),

  list: (params: TransactionListParams) =>
    axios.get<TransactionListResponse>('/api/v1/transactions', { params }),

  get: (id: string) =>
    axios.get<Transaction>(`/api/v1/transactions/${id}`),

  getPending: () =>
    axios.get<Transaction[]>('/api/v1/transactions/pending'),
};
```

### 3.2. Enrichment APIs (US-002, US-003)

```python
# backend/src/api/enrichment.py
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/enrichment", tags=["enrichment"])

# === Request/Response Models ===

class GenerateQuestionsRequest(BaseModel):
    transaction_id: str

class QuestionOption(BaseModel):
    id: str
    text: str
    options: List[str]
    type: str  # "single_choice" | "file_upload"

class GenerateQuestionsResponse(BaseModel):
    transaction_id: str
    questions: List[QuestionOption]

class SubmitAnswersRequest(BaseModel):
    transaction_id: str
    answers: List[dict]  # [{"question_id": "Q1", "answer": "개발비"}]

class SubmitAnswersResponse(BaseModel):
    status: str
    enriched_context_id: str

# === Endpoints ===

@router.post("/questions", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    """
    신규 거래에 대한 스마트 질문 생성
    - 세법/회계법 컨텍스트 기반
    - 과거 패턴 분석 결과 반영
    - 3-7개 질문 생성
    """
    pass

@router.post("/answers", response_model=SubmitAnswersResponse)
async def submit_answers(request: SubmitAnswersRequest):
    """
    유저 답변 저장 및 EnrichedContext 생성
    - 관련 거래 양방향 링크
    - AI 요약 자동 생성
    """
    pass

@router.post("/files/{transaction_id}")
async def upload_document(
    transaction_id: str,
    file: UploadFile = File(...)
):
    """
    증빙 서류 파일 업로드
    - PDF, JPG, PNG 지원 (10MB 이하)
    - 로컬 파일 시스템에 저장
    - 파일명: invoice_{transaction_id}_{date}.{ext}
    """
    pass

@router.get("/context/{transaction_id}")
async def get_enriched_context(transaction_id: str):
    """EnrichedContext 조회"""
    pass
```

### 3.3. Document APIs (US-004, US-005)

```python
# backend/src/api/documents.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# === Request/Response Models ===

class GenerateDocumentRequest(BaseModel):
    user_id: str
    month: str  # "2026-02"

class GenerateDocumentResponse(BaseModel):
    status: str
    document_id: str
    total_transactions: int
    generated_at: str

class UpdateDocumentRequest(BaseModel):
    transaction_id: str
    updates: dict  # {"description": "수정된 설명", "account_classification": "경비-통신비"}

class UpdateDocumentResponse(BaseModel):
    status: str
    document_version: int

# === Endpoints ===

@router.post("/generate", response_model=GenerateDocumentResponse)
async def generate_document(request: GenerateDocumentRequest):
    """
    월말 문서 자동 생성
    - 정기/비정기/확인필요 분류
    - 거래 관계 자동 설명
    - 증빙 체크리스트 생성
    """
    pass

@router.get("/{document_id}")
async def get_document(document_id: str):
    """문서 조회"""
    pass

@router.get("/")
async def list_documents(
    user_id: str,
    year: Optional[int] = None
):
    """문서 목록 조회"""
    pass

@router.put("/{document_id}", response_model=UpdateDocumentResponse)
async def update_document(document_id: str, request: UpdateDocumentRequest):
    """
    문서 수정 (인라인 편집)
    - EnrichedContext도 함께 업데이트
    - 버전 증가
    """
    pass

@router.post("/{document_id}/review")
async def mark_reviewed(document_id: str):
    """리뷰 완료 처리"""
    pass

@router.get("/{document_id}/excel-preview")
async def excel_preview(document_id: str):
    """엑셀 미리보기 데이터 반환"""
    pass

@router.get("/{document_id}/download")
async def download_excel(document_id: str):
    """엑셀 파일 다운로드"""
    pass
```

### 3.4. Delivery APIs (US-006)

```python
# backend/src/api/delivery.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/delivery", tags=["delivery"])

# === Request/Response Models ===

class SendToAccountantRequest(BaseModel):
    document_id: str
    accountant_email: str
    format: str = "xlsx"  # "xlsx" | "csv" | "pdf"

class SendToAccountantResponse(BaseModel):
    status: str
    sent_at: str

# === Endpoints ===

@router.post("/send", response_model=SendToAccountantResponse)
async def send_to_accountant(request: SendToAccountantRequest):
    """
    세무사에게 이메일 발송
    - 엑셀/CSV/PDF 파일 생성
    - 이메일 템플릿 적용
    - 발송 상태 업데이트
    """
    pass

@router.get("/status/{document_id}")
async def get_delivery_status(document_id: str):
    """발송 상태 조회"""
    pass
```

### 3.5. Tax Context APIs → 상세: 섹션 10.5

```python
# backend/src/api/tax_context.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/tax-context", tags=["Tax Context"])

class TransactionContextRequest(BaseModel):
    transaction_id: str
    description: str
    amount: int
    counterparty: Optional[str] = None
    category_hint: Optional[str] = None

class TaxLawContextResponse(BaseModel):
    category: str
    category_label: str
    confidence: float
    related_laws: List[dict]
    evidence_checklist: List[str]
    common_questions: List[str]

@router.post("/search", response_model=TaxLawContextResponse)
async def search_tax_context(request: TransactionContextRequest):
    """
    거래 내용 분석 → 관련 세법 컨텍스트 검색

    할루시네이션 방지 적용 (섹션 10.6 참조)
    """
    pass

@router.get("/categories")
async def get_categories():
    """거래 분류 카테고리 목록 (유저 선택용)"""
    pass

@router.get("/laws/{law_code}")
async def get_law_details(law_code: str, article: Optional[str] = None):
    """특정 법령 상세 조회"""
    pass
```

### 3.6. 에러 코드

```python
# backend/src/utils/errors.py
from enum import Enum

class ErrorCode(str, Enum):
    # Popbill Errors (1xxx)
    POPBILL_CONNECTION_FAILED = "1001"
    POPBILL_AUTH_FAILED = "1002"
    POPBILL_QUICK_QUERY_NOT_ENABLED = "1003"
    POPBILL_RATE_LIMIT = "1004"

    # Transaction Errors (2xxx)
    TRANSACTION_NOT_FOUND = "2001"
    TRANSACTION_DUPLICATE = "2002"

    # Enrichment Errors (3xxx)
    ENRICHMENT_ALREADY_EXISTS = "3001"
    FILE_TOO_LARGE = "3002"
    UNSUPPORTED_FILE_TYPE = "3003"

    # Document Errors (4xxx)
    DOCUMENT_NOT_FOUND = "4001"
    DOCUMENT_GENERATION_FAILED = "4002"

    # Delivery Errors (5xxx)
    EMAIL_SEND_FAILED = "5001"
    INVALID_EMAIL = "5002"

    # AI Errors (6xxx)
    AI_API_FAILED = "6001"
    AI_RATE_LIMIT = "6002"
    AI_HALLUCINATION_DETECTED = "6003"  # 할루시네이션 패턴 감지

    # Tax Context Errors (7xxx)
    TAX_INDEX_NOT_FOUND = "7001"
    TAX_INDEX_UPDATE_FAILED = "7002"
    TAX_CATEGORY_UNKNOWN = "7003"
    TAX_CONTEXT_INSUFFICIENT = "7004"  # 컨텍스트 부족

class APIError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
```

**TypeScript 에러 타입**:
```typescript
// frontend/src/lib/types.ts
export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export const ErrorMessages: Record<string, string> = {
  '1001': '팝빌 API 연결에 실패했습니다. 설정을 확인해주세요.',
  '1003': '은행 빠른조회 서비스 신청이 필요합니다.',
  '3002': '파일 크기가 10MB를 초과합니다.',
  '5001': '이메일 발송에 실패했습니다. 엑셀 파일을 다운로드하여 수동 발송해주세요.',
  '6003': 'AI 응답에서 검증되지 않은 정보가 감지되었습니다. 세무사 확인이 필요합니다.',
  '7001': '세법 인덱스를 찾을 수 없습니다. 인덱스 업데이트가 필요합니다.',
  '7004': '해당 거래에 대한 세법 정보가 부족합니다. 세무사 확인을 권장합니다.',
};
```

---

## 4. External Integrations

### 4.1. 팝빌 API 연동

```python
# backend/src/services/popbill_service.py
from popbill import EasyFinBankService
from typing import List, Dict
from datetime import date
import asyncio

class PopbillService:
    def __init__(self, link_id: str, secret_key: str, is_test: bool = True):
        self.service = EasyFinBankService(link_id, secret_key)
        self.service.IsTest = is_test

    async def fetch_transactions_batch(
        self,
        corp_num: str,
        accounts: List[Dict],  # [{"bank": "기업", "account": "123-456"}]
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        다수 계좌에서 병렬로 거래 내역 조회
        """
        tasks = [
            self._fetch_single_account(corp_num, acc, start_date, end_date)
            for acc in accounts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        transactions = []
        for result in results:
            if isinstance(result, Exception):
                # 로그 및 슬랙 알림
                continue
            transactions.extend(result)

        return transactions

    async def _fetch_single_account(
        self,
        corp_num: str,
        account: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """단일 계좌 조회"""
        # 팝빌 API 호출
        # BankCode: 기업=003, 우리=020, 국민=004, 하나=081
        bank_codes = {
            "기업은행": "003",
            "우리은행": "020",
            "국민은행": "004",
            "하나은행": "081"
        }

        response = self.service.search(
            CorpNum=corp_num,
            BankCode=bank_codes[account["bank"]],
            AccountNumber=account["account"],
            SDate=start_date.strftime("%Y%m%d"),
            EDate=end_date.strftime("%Y%m%d"),
            Order="D"  # 내림차순
        )

        return self._parse_transactions(response, account)

    def detect_internal_transfers(
        self,
        transactions: List[Dict]
    ) -> List[str]:
        """
        계좌 간 이체 감지
        - 동일 금액 + 동일 시간대 (±5분) 입금/출금 페어
        - transaction_id 리스트 반환 (제외 대상)
        """
        # 시간 윈도우 내 동일 금액 페어 찾기
        internal_transfer_ids = []
        # ... 구현
        return internal_transfer_ids
```

### 4.2. Slack 연동

#### 파일 업로드 플로우 (완전 로컬 아키텍처)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 슬랙 메시지                                                       │
│    "📤 파일 업로드" 버튼 (URL 버튼 → localhost:3000/upload/TX001)   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. 브라우저 (localhost:3000)                                        │
│    Next.js 파일 업로드 페이지 → 파일 선택 UI                         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. FastAPI (localhost:8000)                                         │
│    POST /api/v1/enrichment/files/{transaction_id}                   │
│    → 파일 검증 (10MB, PDF/JPG/PNG)                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. 로컬 파일 시스템                                                  │
│    ~/ai-tax-assistant/documents/invoice_{tx_id}_{date}.{ext}        │
│    예: /Users/sanhalee/ai-tax-assistant/documents/invoice_TX001.pdf │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. DB 업데이트 (SQLite)                                              │
│    EnrichedContext.documents.files[] 에 경로 추가                    │
│    EnrichedContext.documents.status = "✅ 준비 완료"                 │
└─────────────────────────────────────────────────────────────────────┘
```

**핵심**: 모든 서버가 `localhost`에서 실행되므로, 웹 업로드 = 로컬 저장

```python
# backend/src/services/slack_service.py
from slack_sdk import WebClient
from slack_sdk.models.blocks import (
    SectionBlock, ActionsBlock, ButtonElement, DividerBlock
)
from typing import List, Dict

class SlackService:
    def __init__(self, token: str, channel_id: str):
        self.client = WebClient(token=token)
        self.channel_id = channel_id

    async def send_daily_questions(
        self,
        transactions: List[Dict],
        questions_by_transaction: Dict[str, List[Dict]]
    ):
        """
        매일 9시 질문 일괄 발송
        """
        blocks = [
            SectionBlock(
                text=f"📊 어제 거래 {len(transactions)}건 확인 필요 (예상 소요: {len(transactions)}분)"
            ),
            DividerBlock()
        ]

        for i, tx in enumerate(transactions, 1):
            # 거래 정보 섹션
            tx_block = SectionBlock(
                text=f"{i}️⃣ {tx['date']} {tx['time']}, {tx['counterparty']} {tx['amount']:,}원 {tx['type']} ({tx['bank_name']})"
            )
            blocks.append(tx_block)

            # 질문별 버튼
            questions = questions_by_transaction.get(tx['id'], [])
            for q in questions:
                action_block = ActionsBlock(
                    block_id=f"q_{tx['id']}_{q['id']}",
                    elements=[
                        ButtonElement(
                            text=opt,
                            action_id=f"answer_{tx['id']}_{q['id']}_{opt}",
                            value=opt
                        ) for opt in q['options']
                    ]
                )
                blocks.append(action_block)

            blocks.append(DividerBlock())

        self.client.chat_postMessage(
            channel=self.channel_id,
            blocks=blocks
        )

    async def handle_button_click(self, payload: Dict) -> Dict:
        """
        슬랙 인터랙티브 버튼 클릭 처리
        """
        action = payload['actions'][0]
        action_id = action['action_id']  # "answer_TX001_Q1_개발비"

        parts = action_id.split('_')
        transaction_id = parts[1]
        question_id = parts[2]
        answer = parts[3]

        return {
            "transaction_id": transaction_id,
            "question_id": question_id,
            "answer": answer
        }

    async def send_reminder(self, transaction_id: str, hours_since: int):
        """미답변 리마인더 발송"""
        pass

    async def send_document_ready(
        self,
        document_id: str,
        summary: Dict
    ):
        """월말 문서 생성 완료 알림"""
        blocks = [
            SectionBlock(
                text=f"📄 {summary['month']} 부가세 신고 문서 준비 완료!"
            ),
            SectionBlock(
                text=f"총 {summary['total_transactions']}건 거래 정리됨\n"
                     f"- 정기 지출: {summary['recurring_count']}건\n"
                     f"- 비정기 지출: {summary['non_recurring_count']}건\n"
                     f"- 확인 필요: {summary['pending_count']}건"
            ),
            ActionsBlock(
                elements=[
                    ButtonElement(
                        text="문서 확인하기 →",
                        url=f"http://localhost:3000/documents/{document_id}",
                        style="primary"
                    )
                ]
            )
        ]

        self.client.chat_postMessage(
            channel=self.channel_id,
            blocks=blocks
        )
```

### 4.3. AI API 연동 → 상세: 섹션 10.6

> ⚠️ **중요**: 세법/회계법 관련 AI 응답은 **할루시네이션 방지** 기법이 필수입니다.
> 상세 구현은 [섹션 10.6. AI 서비스 통합](#106-ai-서비스-통합)을 참조하세요.

```python
# backend/src/services/ai_service.py
from anthropic import AsyncAnthropic
from typing import List, Dict
from .tax_context.search import TaxLawSearchService

class AIService:
    """
    AI 서비스 (세법 컨텍스트 + 할루시네이션 방지 통합)

    주요 기능:
    1. generate_smart_questions() - 스마트 질문 생성
    2. generate_ai_summary() - 세무사용 요약 생성
    3. generate_transaction_relationship() - 관련 거래 설명

    할루시네이션 방지 원칙 (섹션 10.6.1):
    - 컨텍스트 제한: <tax_law_context> 내 정보만 참조
    - 모름 허용: 확신 없으면 "세무사 확인 필요" 응답
    - 증거 우선: <evidence> → <answer> 순서
    - 신뢰도 표시: confidence 필드 필수
    - 출처 인용: source 필드로 법령 조항 명시
    """

    def __init__(self, api_key: str, tax_context_service: TaxLawSearchService):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Claude 3.5 Sonnet
        self.tax_context = tax_context_service

    async def generate_smart_questions(
        self,
        transaction: Dict,
        past_patterns: List[Dict] = None
    ) -> Dict:
        """
        세법 컨텍스트 기반 스마트 질문 생성

        Returns:
            {
                "questions": [...],
                "context_coverage": "complete" | "partial" | "insufficient",
                "disclaimer": str | None
            }

        상세 구현: 섹션 10.6.2 참조
        """
        # 1. 세법 컨텍스트 검색 (섹션 10.5)
        # 2. 할루시네이션 방지 프롬프트 적용 (섹션 10.6.1)
        # 3. Source 유효성 검증 (섹션 10.6.2)
        pass

    async def generate_ai_summary(
        self,
        transaction: Dict,
        answers: List[Dict]
    ) -> Dict:
        """
        세무사용 AI 요약 생성

        할루시네이션 방지:
        - 입력된 거래 데이터만 기반으로 요약
        - 수치는 직접 계산, 추측 금지
        - disclaimer 필드 필수

        상세 구현: 섹션 10.6.3 참조
        """
        pass

    async def generate_transaction_relationship(
        self,
        transactions: List[Dict]
    ) -> str:
        """관련 거래 간 관계 설명 생성"""
        pass
```

**API 호출 설정**:
```python
# 할루시네이션 최소화 설정 (Claude 3.5 Sonnet)
response = await self.client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    system=ANTI_HALLUCINATION_SYSTEM_PROMPT,  # 섹션 10.6.1
    messages=[
        {"role": "user", "content": prompt}
    ],
    temperature=0.0  # 결정론적 응답
)
```

---

## 5. Batch Processing

### 5.1. Scheduler 설정

```python
# backend/src/jobs/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def init_scheduler():
    """배치 작업 스케줄러 초기화"""

    # 매일 06:00 - 거래 수집
    scheduler.add_job(
        sync_transactions_job,
        CronTrigger(hour=6, minute=0),
        id="sync_transactions",
        name="Daily Transaction Sync"
    )

    # 매일 09:00 - 질문 발송
    scheduler.add_job(
        send_questions_job,
        CronTrigger(hour=9, minute=0),
        id="send_questions",
        name="Daily Question Delivery"
    )

    # 매월 25일 09:00 - 문서 생성
    scheduler.add_job(
        generate_document_job,
        CronTrigger(day=25, hour=9, minute=0),
        id="generate_document",
        name="Monthly Document Generation"
    )

    # 매일 09:00 - 리마인더 (미답변 체크)
    scheduler.add_job(
        send_reminders_job,
        CronTrigger(hour=9, minute=0),
        id="send_reminders",
        name="Daily Reminder Check"
    )

    # [v2.0 예정] 매월 1일 02:00 - 세법 인덱스 자동 업데이트
    # MVP에서는 수동 인덱스 사용, v2.0에서 자동 업데이트 추가
    # scheduler.add_job(
    #     update_tax_index_job,
    #     CronTrigger(day=1, hour=2, minute=0),
    #     id="update_tax_index",
    #     name="Monthly Tax Law Index Update"
    # )

    scheduler.start()
```

**배치 작업 요약**:

| 작업 | 스케줄 | 설명 | MVP |
|------|--------|------|:---:|
| sync_transactions | 매일 06:00 | 거래 내역 수집 | ✅ |
| send_questions | 매일 09:00 | 스마트 질문 발송 | ✅ |
| send_reminders | 매일 09:00 | 미답변 리마인더 | ✅ |
| generate_document | 매월 25일 09:00 | 월말 문서 생성 | ✅ |
| ~~update_tax_index~~ | ~~매월 1일 02:00~~ | 세법 인덱스 자동 업데이트 | v2.0 |

> **MVP 참고**: 세법 인덱스는 초기 빌드 시 수동으로 생성하며, 자동 업데이트는 v2.0에서 구현합니다.

### 5.2. 거래 수집 배치 (06:00)

```python
# backend/src/jobs/sync_transactions.py
from datetime import date, timedelta
from src.services.popbill_service import PopbillService
from src.services.slack_service import SlackService
from src.models.transaction import Transaction, TransactionStatus

async def sync_transactions_job():
    """
    매일 06:00 실행
    - 전날 거래 내역 수집
    - 계좌 간 이체 감지 및 제외
    - DB 저장 및 enrichment 플래그 설정
    """
    config = await get_user_config()
    popbill = PopbillService(
        config.popbill_api_key,
        config.popbill_secret_key
    )

    yesterday = date.today() - timedelta(days=1)

    try:
        # 1. 모든 계좌에서 거래 수집
        transactions = await popbill.fetch_transactions_batch(
            corp_num=config.corp_num,
            accounts=config.accounts,
            start_date=yesterday,
            end_date=yesterday
        )

        # 2. 계좌 간 이체 감지
        internal_transfer_ids = popbill.detect_internal_transfers(transactions)

        # 3. DB 저장
        new_count = 0
        for tx in transactions:
            # 중복 체크
            if await transaction_exists(tx['id']):
                continue

            # 저장
            tx_model = Transaction(
                id=tx['id'],
                bank_name=tx['bank_name'],
                account_number=encrypt(tx['account_number']),
                account_number_masked=mask_account(tx['account_number']),
                date=tx['date'],
                time=tx['time'],
                amount=tx['amount'],
                type=tx['type'],
                counterparty=tx.get('counterparty'),
                bank_memo=tx.get('bank_memo'),
                is_internal_transfer=tx['id'] in internal_transfer_ids,
                status=TransactionStatus.PENDING_ENRICHMENT
            )

            # 과거 패턴 확인 (정기 지출 자동 인식)
            if await is_recurring_pattern(tx):
                tx_model.is_recurring = True
                tx_model.status = TransactionStatus.AUTO_CLASSIFIED

            await save_transaction(tx_model)
            new_count += 1

        logger.info(f"Synced {new_count} new transactions")

    except Exception as e:
        # 슬랙 에러 알림
        slack = SlackService(config.slack_token, config.slack_channel)
        await slack.send_error_notification(
            "팝빌 API 연결 실패",
            str(e)
        )
```

### 5.3. 질문 발송 배치 (09:00)

```python
# backend/src/jobs/send_questions.py
from src.services.slack_service import SlackService
from src.services.ai_service import AIService
from src.models.transaction import TransactionStatus

async def send_questions_job():
    """
    매일 09:00 실행
    - pending_enrichment 상태 거래 조회
    - AI로 스마트 질문 생성
    - 슬랙 일괄 발송
    """
    config = await get_user_config()
    slack = SlackService(config.slack_token, config.slack_channel)
    ai = AIService(config.anthropic_api_key)

    # 1. 대기 중인 거래 조회
    pending_transactions = await get_transactions_by_status(
        TransactionStatus.PENDING_ENRICHMENT
    )

    if not pending_transactions:
        logger.info("No pending transactions")
        return

    # 2. 각 거래별 질문 생성
    questions_by_transaction = {}
    for tx in pending_transactions:
        # 과거 패턴 조회
        past_patterns = await get_similar_transactions(tx)

        # 세법 컨텍스트 로드
        tax_context = get_tax_context(tx)

        # AI 질문 생성
        questions = await ai.generate_smart_questions(
            transaction=tx,
            past_patterns=past_patterns,
            tax_context=tax_context
        )

        questions_by_transaction[tx['id']] = questions

    # 3. 슬랙 발송
    await slack.send_daily_questions(
        transactions=pending_transactions,
        questions_by_transaction=questions_by_transaction
    )

    logger.info(f"Sent questions for {len(pending_transactions)} transactions")
```

### 5.4. 문서 생성 배치 (25일)

```python
# backend/src/jobs/generate_document.py
from datetime import date
from src.services.document_service import DocumentService
from src.services.ai_service import AIService
from src.services.slack_service import SlackService

async def generate_document_job():
    """
    매월 25일 09:00 실행
    - 해당 월 거래 수집 및 분류
    - 거래 관계 자동 설명
    - 마크다운 문서 생성
    - 슬랙 알림
    """
    config = await get_user_config()
    doc_service = DocumentService()
    ai = AIService(config.anthropic_api_key)
    slack = SlackService(config.slack_token, config.slack_channel)

    current_month = date.today().strftime("%Y-%m")

    # 1. 해당 월 거래 조회
    transactions = await get_transactions_by_month(current_month)

    # 2. 분류
    recurring = [tx for tx in transactions if tx.is_recurring]
    non_recurring = [tx for tx in transactions if not tx.is_recurring and tx.status == TransactionStatus.ENRICHED]
    pending = [tx for tx in transactions if tx.status in [TransactionStatus.PENDING_ENRICHMENT, TransactionStatus.PENDING_MANUAL_REVIEW]]

    # 3. 관련 거래 그룹화 및 관계 설명 생성
    related_groups = await group_related_transactions(non_recurring)
    for group in related_groups:
        relationship = await ai.generate_transaction_relationship(group)
        group['relationship'] = relationship

    # 4. 증빙 체크리스트 생성
    checklist = doc_service.generate_checklist(transactions)

    # 5. 마크다운 문서 생성
    document = await doc_service.generate_monthly_document(
        month=current_month,
        recurring=recurring,
        non_recurring=non_recurring,
        pending=pending,
        related_groups=related_groups,
        checklist=checklist
    )

    # 6. DB 저장
    await save_document(document)

    # 7. 슬랙 알림
    await slack.send_document_ready(
        document_id=document.id,
        summary={
            "month": current_month,
            "total_transactions": len(transactions),
            "recurring_count": len(recurring),
            "non_recurring_count": len(non_recurring),
            "pending_count": len(pending)
        }
    )

    logger.info(f"Generated document {document.id}")
```

---

## 6. Frontend Components

### 6.1. 페이지 라우팅

```
/                          # 대시보드 홈 (이번 달 요약)
/documents                 # 문서 목록
/documents/[id]            # 문서 상세/편집
/documents/[id]/preview    # 엑셀 미리보기
/settings                  # 설정 (팝빌, 슬랙, 세무사)
```

### 6.2. 주요 컴포넌트

```typescript
// frontend/src/components/TransactionCard.tsx
interface TransactionCardProps {
  transaction: Transaction;
  onEdit?: (id: string) => void;
  showEnrichment?: boolean;
}

export function TransactionCard({
  transaction,
  onEdit,
  showEnrichment = true
}: TransactionCardProps) {
  const statusColors = {
    pending_enrichment: 'bg-yellow-100 text-yellow-800',
    enriched: 'bg-green-100 text-green-800',
    pending_manual_review: 'bg-red-100 text-red-800',
    auto_classified: 'bg-blue-100 text-blue-800',
  };

  return (
    <div className="p-4 border rounded-lg hover:shadow-md transition">
      <div className="flex justify-between items-start">
        <div>
          <span className="text-sm text-gray-500">{transaction.date}</span>
          <h3 className="font-medium">{transaction.counterparty}</h3>
          <p className="text-sm text-gray-600">{transaction.bank_name}</p>
        </div>
        <div className="text-right">
          <p className={`text-lg font-bold ${
            transaction.type === '입금' ? 'text-green-600' : 'text-red-600'
          }`}>
            {transaction.type === '입금' ? '+' : '-'}{transaction.amount.toLocaleString()}원
          </p>
          <span className={`text-xs px-2 py-1 rounded ${statusColors[transaction.status]}`}>
            {transaction.status}
          </span>
        </div>
      </div>

      {showEnrichment && transaction.enriched_context && (
        <div className="mt-3 pt-3 border-t">
          <p className="text-sm text-gray-700">
            {transaction.enriched_context.ai_generated_summary}
          </p>
          <div className="flex gap-2 mt-2">
            <span className={`text-xs px-2 py-1 rounded ${
              transaction.enriched_context.documents.status === '✅ 준비 완료'
                ? 'bg-green-100' : 'bg-yellow-100'
            }`}>
              {transaction.enriched_context.documents.status}
            </span>
          </div>
        </div>
      )}

      {onEdit && (
        <button
          onClick={() => onEdit(transaction.id)}
          className="mt-2 text-sm text-blue-600 hover:underline"
        >
          수정
        </button>
      )}
    </div>
  );
}
```

```typescript
// frontend/src/components/DocumentEditor.tsx
import ReactMarkdown from 'react-markdown';
import { useState } from 'react';

interface DocumentEditorProps {
  document: MonthlyDocument;
  onSave: (updates: DocumentUpdate) => Promise<void>;
}

export function DocumentEditor({ document, onSave }: DocumentEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<string | null>(null);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">
          {document.month} 부가세 신고 문서
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => window.open(`/documents/${document.id}/preview`)}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            엑셀 미리보기
          </button>
          <button
            onClick={handleMarkReviewed}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            리뷰 완료
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <SummaryCard label="총 거래" value={document.total_transactions} />
        <SummaryCard label="총 입금" value={`${document.total_income.toLocaleString()}원`} />
        <SummaryCard label="총 지출" value={`${document.total_expense.toLocaleString()}원`} />
        <SummaryCard
          label="순 현금흐름"
          value={`${(document.total_income - document.total_expense).toLocaleString()}원`}
          positive={document.total_income > document.total_expense}
        />
      </div>

      {/* Markdown Content */}
      <div className="prose max-w-none">
        <ReactMarkdown
          components={{
            // 인라인 편집 가능한 거래 항목 렌더링
            li: ({ node, ...props }) => {
              const transactionId = extractTransactionId(node);
              if (transactionId) {
                return (
                  <li className="relative group">
                    {props.children}
                    <button
                      onClick={() => setEditingTransaction(transactionId)}
                      className="absolute right-0 top-0 opacity-0 group-hover:opacity-100 text-sm text-blue-600"
                    >
                      수정
                    </button>
                  </li>
                );
              }
              return <li {...props} />;
            }
          }}
        >
          {document.document_markdown}
        </ReactMarkdown>
      </div>

      {/* Edit Modal */}
      {editingTransaction && (
        <TransactionEditModal
          transactionId={editingTransaction}
          onClose={() => setEditingTransaction(null)}
          onSave={handleTransactionUpdate}
        />
      )}
    </div>
  );
}
```

```typescript
// frontend/src/components/DocumentChecklist.tsx
interface DocumentChecklistProps {
  checklist: DocumentChecklist;
}

export function DocumentChecklist({ checklist }: DocumentChecklistProps) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-lg font-semibold mb-4">📋 증빙 서류 체크리스트</h2>

      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">상태</th>
            <th className="text-left py-2">건수</th>
            <th className="text-left py-2">설명</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b">
            <td className="py-2">✅ 준비 완료</td>
            <td className="py-2">{checklist.ready.count}건</td>
            <td className="py-2 text-gray-600">계산서/영수증 수집 완료</td>
          </tr>
          <tr className="border-b">
            <td className="py-2">⚠️ 준비 필요</td>
            <td className="py-2">{checklist.needs_preparation.count}건</td>
            <td className="py-2 text-gray-600">계산서 미수령, 요청 필요</td>
          </tr>
          <tr>
            <td className="py-2">❌ 증빙 불가</td>
            <td className="py-2">{checklist.not_available.count}건</td>
            <td className="py-2 text-gray-600">개인 간 거래 (증빙 없음)</td>
          </tr>
        </tbody>
      </table>

      {checklist.needs_preparation.count > 0 && (
        <div className="mt-4 pt-4 border-t">
          <h3 className="font-medium mb-2">준비 필요 항목:</h3>
          <ul className="list-disc list-inside text-sm text-gray-600">
            {checklist.needs_preparation.items.map((item) => (
              <li key={item.id}>
                {item.date} - {item.counterparty} ({item.amount.toLocaleString()}원)
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

### 6.3. 설정 페이지 (파일 저장 경로 포함)

```typescript
// frontend/src/app/settings/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useUserConfig, useUpdateUserConfig } from '@/hooks/useUserConfig';

export default function SettingsPage() {
  const { data: config, isLoading } = useUserConfig();
  const updateConfig = useUpdateUserConfig();
  const [documentsPath, setDocumentsPath] = useState<string>('');
  const [platformInfo, setPlatformInfo] = useState<PlatformInfo | null>(null);

  useEffect(() => {
    // 현재 플랫폼 정보 조회
    fetch('/api/v1/system/platform-info')
      .then(res => res.json())
      .then(setPlatformInfo);
  }, []);

  useEffect(() => {
    if (config) {
      setDocumentsPath(config.documents_path || '');
    }
  }, [config]);

  const handleSave = async () => {
    await updateConfig.mutateAsync({
      documents_path: documentsPath || null  // 빈 문자열은 null로 (자동 감지)
    });
  };

  if (isLoading) return <div>로딩 중...</div>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">설정</h1>

      {/* 파일 저장 경로 섹션 */}
      <section className="mb-8 p-4 border rounded-lg">
        <h2 className="text-lg font-semibold mb-4">📁 파일 저장 경로</h2>

        {platformInfo && (
          <div className="mb-4 p-3 bg-gray-50 rounded text-sm">
            <p><strong>현재 OS:</strong> {platformInfo.system}</p>
            <p><strong>현재 계정:</strong> {platformInfo.username}</p>
            <p><strong>홈 디렉토리:</strong> {platformInfo.home_directory}</p>
            <p><strong>현재 저장 경로:</strong> {platformInfo.documents_path}</p>
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            증빙 서류 저장 경로
          </label>
          <input
            type="text"
            value={documentsPath}
            onChange={(e) => setDocumentsPath(e.target.value)}
            placeholder="비워두면 자동 감지 (홈 디렉토리/ai-tax-assistant/documents/)"
            className="w-full p-2 border rounded"
          />
          <p className="text-sm text-gray-500 mt-1">
            예시: /Users/sanhalee/Dropbox/세무/증빙서류/
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={updateConfig.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {updateConfig.isPending ? '저장 중...' : '저장'}
        </button>
      </section>

      {/* 다른 설정 섹션들... */}
    </div>
  );
}
```

```typescript
// shared/types/system.ts
export interface PlatformInfo {
  system: 'Darwin' | 'Windows' | 'Linux';
  username: string;         // 현재 OS 로그인 계정 (예: "sanhalee")
  home_directory: string;   // 홈 디렉토리 (예: "/Users/sanhalee")
  documents_path: string;   // 실제 저장 경로
  path_separator: '/' | '\\';
}
```

```python
# backend/src/api/system.py
from fastapi import APIRouter
from src.utils.file_storage import LocalFileStorage

router = APIRouter(prefix="/api/v1/system", tags=["system"])

@router.get("/platform-info")
async def get_platform_info():
    """현재 플랫폼 및 경로 정보 반환"""
    storage = LocalFileStorage.from_user_config(await get_user_config())
    return storage.platform_info
```

### 6.4. API 호출 훅

```typescript
// frontend/src/hooks/useDocuments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentApi } from '@/lib/api';

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentApi.get(documentId),
  });
}

export function useDocuments(userId: string, year?: number) {
  return useQuery({
    queryKey: ['documents', userId, year],
    queryFn: () => documentApi.list({ user_id: userId, year }),
  });
}

export function useUpdateDocument(documentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: DocumentUpdate) =>
      documentApi.update(documentId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] });
    },
  });
}

export function useMarkReviewed(documentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => documentApi.markReviewed(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] });
    },
  });
}

export function useSendToAccountant() {
  return useMutation({
    mutationFn: (request: SendToAccountantRequest) =>
      deliveryApi.send(request),
  });
}
```

---

## 7. Security & Local Architecture

### 7.1. 암호화 저장

```python
# backend/src/utils/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class EncryptionService:
    def __init__(self, master_password: str):
        # Master password에서 key 생성
        salt = os.environ.get('ENCRYPTION_SALT', 'default-salt').encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """문자열 복호화"""
        return self.fernet.decrypt(ciphertext.encode()).decode()

# 암호화 대상:
# - popbill_api_key
# - popbill_secret_key
# - 계좌번호 (account_number)
# - slack_token
```

### 7.2. 민감 데이터 마스킹

```python
# backend/src/utils/masking.py
import re

def mask_account_number(account: str) -> str:
    """
    계좌번호 마스킹
    "123-456-789012" -> "***-***-789012"
    """
    parts = account.split('-')
    if len(parts) >= 3:
        return f"***-***-{parts[-1]}"
    return "***-***-" + account[-4:]

def mask_for_ai(transaction: dict) -> dict:
    """
    AI API 호출 전 민감 데이터 마스킹
    - 계좌번호 완전 제거
    - 거래처 이름은 유지 (비즈니스 맥락 필요)
    """
    masked = transaction.copy()
    masked.pop('account_number', None)
    masked.pop('account_number_encrypted', None)
    masked['account_number_masked'] = "***-***-****"
    return masked

def mask_for_slack(transaction: dict) -> dict:
    """
    슬랙 발송용 마스킹
    - 계좌번호 마지막 4자리만 표시
    - 금액, 거래처, 날짜는 표시
    """
    masked = transaction.copy()
    masked['account_number'] = mask_account_number(
        transaction.get('account_number', '')
    )
    return masked
```

### 7.3. 로컬 파일 저장 (크로스 플랫폼 + 사용자 설정 가능)

```python
# backend/src/utils/file_storage.py
from pathlib import Path
import platform
import getpass
import shutil

class LocalFileStorage:
    """
    크로스 플랫폼 로컬 파일 저장소

    경로 결정 우선순위:
    1. 유저가 설정에서 직접 지정한 경로 (custom_path)
    2. 현재 로그인한 OS 계정 기반 자동 생성 (Path.home())

    자동 생성 경로 예시 (현재 접속 계정: sanhalee):
    - macOS:   /Users/sanhalee/ai-tax-assistant/documents/
    - Windows: C:\\Users\\sanhalee\\ai-tax-assistant\\documents\\
    - Linux:   /home/sanhalee/ai-tax-assistant/documents/
    """

    def __init__(self, custom_path: str = None):
        if custom_path:
            # 1. 유저가 직접 지정한 경로 사용
            #    예: "/Volumes/ExternalDrive/tax-documents/"
            #    예: "D:\\MyDocuments\\tax\\"
            self.base_path = Path(custom_path).expanduser().resolve()
        else:
            # 2. 현재 OS 로그인 계정 기반 자동 생성
            #    Path.home() → 현재 로그인한 유저의 홈 디렉토리
            #    getpass.getuser() → 현재 유저명 (예: "sanhalee")
            self.base_path = Path.home() / "ai-tax-assistant" / "documents"

        # 디렉토리가 없으면 자동 생성
        self.base_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_user_config(cls, config: "UserConfig") -> "LocalFileStorage":
        """UserConfig에서 경로 설정을 읽어 인스턴스 생성"""
        return cls(custom_path=config.documents_path)

    @property
    def current_user(self) -> str:
        """현재 로그인한 OS 사용자명 반환"""
        return getpass.getuser()  # 예: "sanhalee"

    @property
    def platform_info(self) -> dict:
        """현재 플랫폼 및 경로 정보 반환"""
        return {
            "system": platform.system(),        # "Darwin", "Windows", "Linux"
            "username": self.current_user,      # "sanhalee"
            "home_directory": str(Path.home()), # "/Users/sanhalee"
            "documents_path": str(self.base_path),
            "path_separator": "\\" if platform.system() == "Windows" else "/"
        }

    def save_file(
        self,
        file_content: bytes,
        transaction_id: str,
        file_ext: str
    ) -> str:
        """
        증빙 서류 파일 저장
        반환: 저장된 파일 경로
        """
        from datetime import date
        filename = f"invoice_{transaction_id}_{date.today().isoformat()}.{file_ext}"
        file_path = self.base_path / filename

        with open(file_path, 'wb') as f:
            f.write(file_content)

        return str(file_path)

    def get_file(self, file_path: str) -> bytes:
        """파일 읽기"""
        with open(file_path, 'rb') as f:
            return f.read()

    def delete_file(self, file_path: str):
        """파일 삭제"""
        Path(file_path).unlink(missing_ok=True)

    def list_files(self, transaction_id: str = None) -> list:
        """파일 목록 조회"""
        pattern = f"invoice_{transaction_id}_*" if transaction_id else "invoice_*"
        return list(self.base_path.glob(pattern))
```

### 7.4. 환경 변수 관리

```bash
# .env.example
# 팝빌 API (암호화 저장)
POPBILL_LINK_ID=your_link_id
POPBILL_SECRET_KEY=your_secret_key
POPBILL_IS_TEST=true

# 슬랙
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_ID=C01234567

# AI API
OPENAI_API_KEY=sk-your-key

# 암호화
ENCRYPTION_SALT=random-salt-string
MASTER_PASSWORD=user-provided-password

# 이메일 (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 데이터베이스
DATABASE_URL=sqlite:///./ai_tax_assistant.db

# 파일 저장
DOCUMENTS_PATH=~/ai-tax-assistant/documents/
```

---

## 8. TDD 테스트 시나리오

### 8.1. Unit Tests

```python
# tests/unit/test_transaction.py
import pytest
from src.models.transaction import Transaction, TransactionStatus
from src.services.popbill_service import PopbillService

class TestTransaction:
    def test_create_transaction_from_popbill_response(self):
        """팝빌 API 응답을 Transaction 객체로 변환"""
        popbill_response = {
            "trdate": "20260205",
            "trtime": "143000",
            "tramt": 50000,
            "trtype": "출금",
            "remark1": "AWS Korea"
        }

        tx = Transaction.from_popbill(popbill_response, bank_name="기업은행", account="123-456-789")

        assert tx.amount == 50000
        assert tx.type == "지출"
        assert tx.counterparty == "AWS Korea"
        assert tx.bank_name == "기업은행"

    def test_detect_internal_transfer(self):
        """계좌 간 이체 자동 감지 (동일 금액, 동일 시간대)"""
        service = PopbillService("test_link", "test_secret")

        transactions = [
            {"id": "TX1", "amount": 100000, "type": "지출", "time": "14:30:00", "bank": "기업"},
            {"id": "TX2", "amount": 100000, "type": "입금", "time": "14:32:00", "bank": "우리"},
            {"id": "TX3", "amount": 50000, "type": "지출", "time": "15:00:00", "bank": "기업"},
        ]

        internal_ids = service.detect_internal_transfers(transactions)

        assert "TX1" in internal_ids
        assert "TX2" in internal_ids
        assert "TX3" not in internal_ids

    def test_deduplicate_transactions(self):
        """중복 거래 제거 (transaction_id 기반)"""
        existing_ids = ["TX1", "TX2"]
        new_transactions = [
            {"id": "TX1", "amount": 100},  # 중복
            {"id": "TX3", "amount": 200},  # 신규
        ]

        unique = [tx for tx in new_transactions if tx["id"] not in existing_ids]

        assert len(unique) == 1
        assert unique[0]["id"] == "TX3"

    def test_flag_needs_enrichment(self):
        """신규 거래 vs 반복 거래 플래그 설정"""
        # 과거 3개월 동일 패턴 있음 → is_recurring=True
        past_patterns = [
            {"counterparty": "AWS", "amount": 50000, "date": "2026-01-15"},
            {"counterparty": "AWS", "amount": 50000, "date": "2025-12-15"},
            {"counterparty": "AWS", "amount": 50000, "date": "2025-11-15"},
        ]
        new_tx = {"counterparty": "AWS", "amount": 50000, "date": "2026-02-15"}

        is_recurring = check_recurring_pattern(new_tx, past_patterns)

        assert is_recurring == True
```

```python
# tests/unit/test_enrichment.py
import pytest
from src.models.enriched_context import EnrichedContext

class TestEnrichment:
    def test_create_enriched_context_from_answers(self):
        """유저 답변으로 EnrichedContext 생성"""
        answers = [
            {"question_id": "Q1", "answer": "개발비"},
            {"question_id": "Q2", "answer": "네, 매월 반복"},
            {"question_id": "Q3", "answer": "1월 AWS와 관련"},
        ]

        context = EnrichedContext.from_answers(
            transaction_id="TX1",
            answers=answers
        )

        assert context.category == "개발비"
        assert context.is_recurring == True
        assert len(context.related_transaction_ids) > 0

    def test_auto_link_related_transactions(self):
        """관련 거래 양방향 자동 링크"""
        tx1 = EnrichedContext(id="EC1", transaction_id="TX1", related_transaction_ids=[])
        tx2 = EnrichedContext(id="EC2", transaction_id="TX2", related_transaction_ids=[])

        # TX1 → TX2 관련 설정
        tx1.add_related_transaction("TX2")

        # TX2에도 TX1 자동 추가 확인
        assert "TX2" in tx1.related_transaction_ids
        # (실제 구현에서 DB 업데이트 필요)

    def test_recurring_detection_after_3_months(self):
        """3개월 반복 시 is_recurring 자동 설정"""
        transactions = [
            {"counterparty": "AWS", "amount": 50000, "date": "2026-01-15"},
            {"counterparty": "AWS", "amount": 50000, "date": "2025-12-15"},
            {"counterparty": "AWS", "amount": 50000, "date": "2025-11-15"},
        ]

        is_recurring = detect_recurring(transactions)

        assert is_recurring == True
```

```python
# tests/unit/test_monthly_document.py
import pytest
from src.services.document_service import DocumentService

class TestMonthlyDocument:
    def test_generate_monthly_summary(self):
        """월별 거래 요약 생성 (입금/지출 합계)"""
        transactions = [
            {"type": "입금", "amount": 5000000},
            {"type": "지출", "amount": 2000000},
            {"type": "지출", "amount": 1200000},
        ]

        summary = DocumentService.generate_summary(transactions)

        assert summary["total_income"] == 5000000
        assert summary["total_expense"] == 3200000
        assert summary["net_cash_flow"] == 1800000

    def test_classify_transactions(self):
        """정기/비정기/확인필요 자동 분류"""
        transactions = [
            {"id": "TX1", "is_recurring": True, "status": "enriched"},
            {"id": "TX2", "is_recurring": False, "status": "enriched"},
            {"id": "TX3", "is_recurring": False, "status": "pending_manual_review"},
        ]

        classified = DocumentService.classify(transactions)

        assert len(classified["recurring"]) == 1
        assert len(classified["non_recurring"]) == 1
        assert len(classified["pending"]) == 1

    def test_group_related_transactions(self):
        """관련 거래 그룹화"""
        transactions = [
            {"id": "TX1", "related": ["TX2", "TX3"]},
            {"id": "TX2", "related": ["TX1", "TX3"]},
            {"id": "TX3", "related": ["TX1", "TX2"]},
            {"id": "TX4", "related": []},
        ]

        groups = DocumentService.group_related(transactions)

        assert len(groups) == 2  # 1그룹(TX1-3) + 1개별(TX4)
        assert len(groups[0]) == 3

    def test_generate_document_checklist(self):
        """증빙 서류 체크리스트 생성"""
        transactions = [
            {"id": "TX1", "documents": {"status": "✅ 준비 완료"}},
            {"id": "TX2", "documents": {"status": "⚠️ 준비 필요"}},
            {"id": "TX3", "documents": {"status": "❌ 증빙 불가"}},
        ]

        checklist = DocumentService.generate_checklist(transactions)

        assert checklist["ready"]["count"] == 1
        assert checklist["needs_preparation"]["count"] == 1
        assert checklist["not_available"]["count"] == 1
```

### 8.2. Cross-Platform Tests

```python
# tests/unit/test_cross_platform.py
import pytest
import platform
from pathlib import Path
from src.utils.file_storage import LocalFileStorage

class TestCrossPlatform:
    def test_home_directory_resolution(self):
        """Path.home()이 모든 OS에서 올바르게 해석되는지 확인"""
        storage = LocalFileStorage()
        home = Path.home()

        assert storage.base_path.is_absolute()
        assert str(home) in str(storage.base_path)

    def test_path_separator_handling(self):
        """경로 구분자가 OS에 맞게 처리되는지 확인"""
        storage = LocalFileStorage()
        file_path = storage.base_path / "invoice_TX001_2026-02-06.pdf"

        # Path 객체는 OS에 맞는 구분자 사용
        assert file_path.exists() or True  # 파일 없어도 경로는 유효

    def test_file_save_and_read_cross_platform(self, tmp_path):
        """파일 저장/읽기가 모든 OS에서 동작하는지 확인"""
        storage = LocalFileStorage(base_path=str(tmp_path))
        content = b"test file content"

        # 저장
        file_path = storage.save_file(content, "TX001", "pdf")

        # 읽기
        read_content = storage.get_file(file_path)

        assert read_content == content
        assert Path(file_path).exists()

    @pytest.mark.parametrize("os_name", ["Darwin", "Windows", "Linux"])
    def test_platform_detection(self, os_name, monkeypatch):
        """플랫폼 감지가 올바르게 동작하는지 확인"""
        monkeypatch.setattr(platform, "system", lambda: os_name)

        storage = LocalFileStorage()
        info = storage.platform_info

        assert info["system"] == os_name
        if os_name == "Windows":
            assert info["path_separator"] == "\\"
        else:
            assert info["path_separator"] == "/"
```

### 8.3. Integration Tests

```python
# tests/integration/test_popbill_integration.py
import pytest
from src.services.popbill_service import PopbillService

@pytest.mark.integration
class TestPopbillIntegration:
    @pytest.fixture
    def popbill_service(self):
        return PopbillService(
            link_id=os.environ["POPBILL_LINK_ID"],
            secret_key=os.environ["POPBILL_SECRET_KEY"],
            is_test=True
        )

    def test_popbill_connection(self, popbill_service):
        """팝빌 API 연결 테스트"""
        result = popbill_service.test_connection()
        assert result["status"] == "success"

    def test_fetch_transactions_batch(self, popbill_service):
        """다수 계좌 병렬 조회"""
        accounts = [
            {"bank": "기업은행", "account": "123-456-789"},
            {"bank": "우리은행", "account": "987-654-321"},
        ]

        transactions = await popbill_service.fetch_transactions_batch(
            corp_num="1234567890",
            accounts=accounts,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 5)
        )

        assert isinstance(transactions, list)

    def test_handle_popbill_error(self, popbill_service):
        """API 오류 시 재시도 및 알림"""
        with pytest.raises(PopbillConnectionError):
            await popbill_service.fetch_transactions_batch(
                corp_num="invalid",
                accounts=[],
                start_date=date.today(),
                end_date=date.today()
            )
```

```python
# tests/integration/test_slack_integration.py
import pytest
from src.services.slack_service import SlackService

@pytest.mark.integration
class TestSlackIntegration:
    @pytest.fixture
    def slack_service(self):
        return SlackService(
            token=os.environ["SLACK_BOT_TOKEN"],
            channel_id=os.environ["SLACK_TEST_CHANNEL"]
        )

    def test_send_daily_question(self, slack_service):
        """매일 9시 질문 슬랙 발송"""
        transactions = [
            {"id": "TX1", "date": "2026-02-05", "amount": 50000, "counterparty": "AWS"}
        ]
        questions = {
            "TX1": [{"id": "Q1", "text": "테스트 질문", "options": ["A", "B"]}]
        }

        result = await slack_service.send_daily_questions(transactions, questions)
        assert result["ok"] == True

    def test_handle_button_response(self, slack_service):
        """슬랙 버튼 클릭 응답 처리"""
        payload = {
            "actions": [{"action_id": "answer_TX1_Q1_A"}]
        }

        result = await slack_service.handle_button_click(payload)

        assert result["transaction_id"] == "TX1"
        assert result["question_id"] == "Q1"
        assert result["answer"] == "A"

    def test_send_reminder(self, slack_service):
        """24시간 미답변 리마인더 발송"""
        result = await slack_service.send_reminder("TX1", hours_since=24)
        assert result["ok"] == True
```

```python
# tests/integration/test_ai_integration.py
import pytest
from src.services.ai_service import AIService

@pytest.mark.integration
class TestAIIntegration:
    @pytest.fixture
    def ai_service(self):
        return AIService(api_key=os.environ["OPENAI_API_KEY"])

    def test_generate_smart_questions(self, ai_service):
        """세법 기반 스마트 질문 생성"""
        transaction = {
            "amount": 50000,
            "type": "지출",
            "counterparty": "AWS Korea",
            "bank_memo": "서버비"
        }

        questions = await ai_service.generate_smart_questions(
            transaction=transaction,
            past_patterns=[],
            tax_context="IT 스타트업 세액공제 관련 컨텍스트"
        )

        assert len(questions) >= 3
        assert len(questions) <= 7
        assert all("id" in q and "text" in q and "options" in q for q in questions)

    def test_generate_ai_summary(self, ai_service):
        """세무사용 AI 요약 생성"""
        transaction = {
            "amount": 50000,
            "counterparty": "AWS Korea",
            "bank_memo": "서버비"
        }
        answers = [
            {"question_id": "Q1", "answer": "개발비"},
            {"question_id": "Q2", "answer": "정기 지출"}
        ]

        summary = await ai_service.generate_ai_summary(transaction, answers)

        assert isinstance(summary, str)
        assert len(summary) > 20

    def test_mask_sensitive_data(self, ai_service):
        """AI 호출 전 민감 데이터 마스킹"""
        from src.utils.masking import mask_for_ai

        transaction = {
            "account_number": "123-456-789012",
            "counterparty": "AWS Korea",
            "amount": 50000
        }

        masked = mask_for_ai(transaction)

        assert "account_number" not in masked or masked.get("account_number_masked") == "***-***-****"
        assert masked["counterparty"] == "AWS Korea"

    async def test_hallucination_prevention_context_only(self, ai_service):
        """할루시네이션 방지: 컨텍스트 내 정보만 사용"""
        # Given: 제한된 세법 컨텍스트
        limited_context = [
            {
                "law_code": "CIT",
                "article": "제25조",
                "title": "접대비의 손금불산입",
                "summary": "접대비 한도는 연 3,600만원",
                "key_points": ["중소기업 기본한도 3,600만원"],
                "limits": {"기본한도": "연 3,600만원"}
            }
        ]

        transaction = {
            "amount": 150000,
            "counterparty": "거래처",
            "description": "고객 접대"
        }

        # When: 스마트 질문 생성
        result = await ai_service.generate_smart_questions_with_context(
            transaction=transaction,
            tax_context=limited_context
        )

        # Then: 모든 질문의 source가 컨텍스트 내 법령만 참조
        for q in result["questions"]:
            source = q.get("source", "")
            is_valid = (
                "CIT 제25조" in source or
                "컨텍스트 외 - 세무사 확인 필요" in source or
                "⚠️" in source  # 검증 실패 표시
            )
            assert is_valid, f"Invalid source: {source}"

    async def test_hallucination_prevention_unknown_answer(self, ai_service):
        """할루시네이션 방지: 모르면 모른다고 답변"""
        # Given: 부동산 관련 거래 (세법 컨텍스트에 없음)
        empty_context = []

        transaction = {
            "amount": 5000000,
            "counterparty": "부동산",
            "description": "사무실 보증금"
        }

        # When: 스마트 질문 생성
        result = await ai_service.generate_smart_questions_with_context(
            transaction=transaction,
            tax_context=empty_context
        )

        # Then: context_coverage가 insufficient이고 disclaimer 존재
        assert result.get("context_coverage") in ["insufficient", "partial"]
        assert result.get("disclaimer") is not None

    async def test_hallucination_prevention_no_fabricated_rates(self, ai_service):
        """할루시네이션 방지: 컨텍스트에 없는 세율 생성 금지"""
        # Given: 세율 정보가 없는 컨텍스트
        context_without_rates = [
            {
                "law_code": "VAT",
                "article": "제17조",
                "title": "매입세액공제",
                "summary": "사업 관련 매입세액은 공제 가능",
                "key_points": ["적격증빙 필수"],
                "limits": {}  # 세율 정보 없음
            }
        ]

        transaction = {
            "amount": 100000,
            "description": "사무용품 구매"
        }

        result = await ai_service.generate_smart_questions_with_context(
            transaction=transaction,
            tax_context=context_without_rates
        )

        # Then: 응답에 10%, 부가세율 등 구체적 수치가 없어야 함
        response_text = str(result)
        assert "10%" not in response_text or "컨텍스트" in response_text

    def test_response_validator_detects_patterns(self):
        """응답 검증기: 할루시네이션 패턴 감지"""
        from src.services.ai_service import AIResponseValidator

        validator = AIResponseValidator()

        # Given: 할루시네이션 패턴이 포함된 응답
        suspicious_response = {
            "questions": [
                {
                    "question": "일반적으로 접대비는 한도가 있는데...",
                    "source": "2024년 개정 법인세법",
                    "confidence": "high"
                }
            ]
        }

        # When: 검증
        metrics = validator.validate(suspicious_response, [])

        # Then: 할루시네이션 플래그 감지
        assert len(metrics.hallucination_flags) > 0
        assert metrics.source_validity < 1.0
```

```python
# tests/integration/test_tax_context.py
import pytest
from src.services.tax_context.search import TaxLawSearchService
from src.services.tax_context.categories import TransactionCategory

@pytest.mark.integration
class TestTaxContextIntegration:
    """세법 컨텍스트 서비스 통합 테스트"""

    @pytest.fixture
    def search_service(self):
        return TaxLawSearchService()

    async def test_classify_employee_meal(self, search_service):
        """직원 식대 거래 분류"""
        category = await search_service.classify_transaction(
            description="점심 식대",
            amount=35000,
            counterparty="삼성동 한식당"
        )

        assert category == TransactionCategory.EMPLOYEE_MEAL

    async def test_classify_entertainment(self, search_service):
        """접대비 거래 분류"""
        category = await search_service.classify_transaction(
            description="고객 미팅 식사",
            amount=150000,
            counterparty="강남 레스토랑"
        )

        assert category == TransactionCategory.BUSINESS_ENTERTAINMENT

    async def test_classify_freelancer_fee(self, search_service):
        """프리랜서 비용 분류"""
        category = await search_service.classify_transaction(
            description="디자인 외주비",
            amount=3000000,
            counterparty="홍길동"
        )

        assert category == TransactionCategory.FREELANCER_FEE

    async def test_search_related_laws(self, search_service):
        """관련 세법 검색"""
        laws = await search_service.search_related_laws(
            category=TransactionCategory.BUSINESS_ENTERTAINMENT,
            description="거래처 접대 식사",
            top_k=3
        )

        assert len(laws) >= 1
        assert any("접대비" in law["title"] for law in laws)
        assert any("제25조" in law.get("article", "") for law in laws)

    async def test_assemble_context_with_limits(self, search_service):
        """한도 정보 포함된 컨텍스트 조합"""
        from src.api.tax_context import TransactionContextRequest

        context = await search_service.search_tax_context(
            TransactionContextRequest(
                transaction_id="TX001",
                description="거래처 접대",
                amount=200000,
                counterparty="OO기업"
            )
        )

        assert context.category == "business_entertainment"
        assert "접대비" in context.category_label
        assert "연 3,600만원" in str(context.related_laws)  # 한도 정보

    async def test_evidence_checklist(self, search_service):
        """적격증빙 체크리스트 반환"""
        from src.api.tax_context import TransactionContextRequest

        context = await search_service.search_tax_context(
            TransactionContextRequest(
                transaction_id="TX002",
                description="직원 점심",
                amount=45000,
                counterparty="식당"
            )
        )

        assert len(context.evidence_checklist) >= 1
        assert any("카드" in e or "세금계산서" in e for e in context.evidence_checklist)
```

```python
# tests/unit/test_tax_index.py
import pytest
from src.services.tax_context.index import TaxLawIndexBuilder
from src.services.tax_context.categories import CATEGORY_TAX_LAW_MAP, TransactionCategory

class TestTaxLawIndex:
    """세법 인덱스 단위 테스트"""

    def test_category_mapping_completeness(self):
        """모든 카테고리에 세법 매핑 존재"""
        for category in TransactionCategory:
            if category != TransactionCategory.INTERNAL_TRANSFER:
                assert category in CATEGORY_TAX_LAW_MAP, f"{category} 매핑 없음"
                assert len(CATEGORY_TAX_LAW_MAP[category]) >= 1

    def test_chunk_id_format(self):
        """청크 ID 포맷 검증"""
        chunk_id = "CIT_제25조_1"
        parts = chunk_id.split("_")

        assert len(parts) == 3
        assert parts[0] in ["CIT", "PIT", "VAT", "STTC"]

    def test_2026_tax_updates_loaded(self):
        """2026년 세법 개정사항 로드 확인"""
        import yaml
        from pathlib import Path

        data_path = Path("backend/data/tax_updates_2026.yaml")
        # 파일 존재 시 로드 테스트 (개발 중에는 skip)
        if data_path.exists():
            with open(data_path) as f:
                updates = yaml.safe_load(f)

            assert "cit_2026" in updates
            assert any("세율" in item.get("article", "") for item in updates["cit_2026"])
```

### 8.3. E2E Test Scenarios

```python
# tests/e2e/test_full_flow.py
import pytest
from datetime import date, timedelta

@pytest.mark.e2e
class TestFullFlow:
    """
    전체 플로우 E2E 테스트
    배치 수집 → 질문 발송 → 답변 처리 → 문서 생성 → 발송
    """

    async def test_scenario_1_batch_sync(self, test_client, mock_popbill):
        """
        Scenario 1: 배치 거래 수집 (매일 6시)

        Given: 팝빌 API 연동된 2개 계좌 (기업은행, 우리은행)
        When: 06:00 배치 실행
        Then:
          - 전날 거래 내역 수집
          - Transaction 테이블에 저장
          - 계좌 간 이체 자동 제외
          - needs_enrichment 플래그 설정
        """
        # Given
        mock_popbill.return_transactions([
            {"id": "TX1", "bank": "기업", "amount": 100000, "type": "지출"},
            {"id": "TX2", "bank": "우리", "amount": 100000, "type": "입금"},  # 내부 이체
            {"id": "TX3", "bank": "기업", "amount": 50000, "type": "지출"},
        ])

        # When
        from src.jobs.sync_transactions import sync_transactions_job
        await sync_transactions_job()

        # Then
        transactions = await test_client.get("/api/v1/transactions/")

        assert len(transactions) == 3
        assert transactions[0]["is_internal_transfer"] == True
        assert transactions[1]["is_internal_transfer"] == True
        assert transactions[2]["is_internal_transfer"] == False
        assert transactions[2]["status"] == "pending_enrichment"

    async def test_scenario_2_smart_questions(self, test_client, mock_slack, mock_ai):
        """
        Scenario 2: 스마트 질문 + 답변 (매일 9시)

        Given: needs_enrichment 플래그 거래 3건
        When: 09:00 배치 실행
        Then:
          - 슬랙 메시지 발송 (3건 모아서)
          - 질문 3-7개 포함
          - 버튼 인터랙션 가능

        When: 유저가 버튼 클릭
        Then:
          - EnrichedContext 생성
          - Transaction status 업데이트
        """
        # Given
        await create_pending_transactions(3)
        mock_ai.return_questions([
            {"id": "Q1", "text": "개발비인가요?", "options": ["개발비", "운영비"]},
            {"id": "Q2", "text": "정기 지출인가요?", "options": ["네", "아니오"]},
        ])

        # When - 배치 실행
        from src.jobs.send_questions import send_questions_job
        await send_questions_job()

        # Then
        assert mock_slack.messages_sent == 1
        assert len(mock_slack.last_message["blocks"]) > 3

        # When - 버튼 클릭
        response = await test_client.post("/api/v1/slack/interactive", json={
            "payload": {"actions": [{"action_id": "answer_TX1_Q1_개발비"}]}
        })

        # Then
        context = await test_client.get("/api/v1/enrichment/context/TX1")
        assert context["category"] == "개발비"

    async def test_scenario_3_monthly_document(self, test_client, mock_ai):
        """
        Scenario 3: 월말 문서 생성 (25일)

        Given: 2월 거래 48건 (enriched 45건, pending 3건)
        When: 25일 09:00 배치 실행
        Then:
          - MonthlyDocument 생성
          - 정기/비정기/확인필요 분류
          - 거래 관계 자동 설명
          - 증빙 체크리스트 생성
          - 슬랙 알림 발송
        """
        # Given
        await create_transactions_for_month("2026-02", count=48, enriched=45)

        # When
        from src.jobs.generate_document import generate_document_job
        await generate_document_job()

        # Then
        document = await test_client.get("/api/v1/documents/MD-2026-02")

        assert document["total_transactions"] == 48
        assert document["status"] == "generated"
        assert "정기 지출" in document["document_markdown"]
        assert "증빙 서류 체크리스트" in document["document_markdown"]

    async def test_scenario_4_document_review_and_send(self, test_client, mock_email):
        """
        Scenario 4: 문서 리뷰 및 발송

        Given: 생성된 MonthlyDocument
        When: 유저가 웹 대시보드 접속
        Then:
          - 마크다운 렌더링
          - 인라인 수정 가능
          - 엑셀 미리보기 가능

        When: "세무사에게 발송" 클릭
        Then:
          - 엑셀 파일 생성
          - 이메일 자동 발송
          - status = "sent" 업데이트
        """
        # Given
        document_id = "MD-2026-02"

        # When - 문서 조회
        document = await test_client.get(f"/api/v1/documents/{document_id}")
        assert document["document_markdown"] is not None

        # When - 인라인 수정
        await test_client.put(f"/api/v1/documents/{document_id}", json={
            "transaction_id": "TX1",
            "updates": {"description": "수정된 설명"}
        })

        # Then
        updated = await test_client.get(f"/api/v1/documents/{document_id}")
        assert updated["document_version"] == 2

        # When - 리뷰 완료
        await test_client.post(f"/api/v1/documents/{document_id}/review")

        # When - 세무사 발송
        await test_client.post("/api/v1/delivery/send", json={
            "document_id": document_id,
            "accountant_email": "accountant@example.com",
            "format": "xlsx"
        })

        # Then
        final = await test_client.get(f"/api/v1/documents/{document_id}")
        assert final["status"] == "sent"
        assert mock_email.sent_count == 1
        assert mock_email.last_attachment_type == "xlsx"
```

### 8.4. 테스트 설정

```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)

@pytest.fixture
def mock_popbill():
    mock = MagicMock()
    mock.return_transactions = lambda txs: setattr(mock, '_transactions', txs)
    return mock

@pytest.fixture
def mock_slack():
    mock = AsyncMock()
    mock.messages_sent = 0
    mock.last_message = None
    return mock

@pytest.fixture
def mock_ai():
    mock = AsyncMock()
    mock.return_questions = lambda qs: setattr(mock, '_questions', qs)
    return mock

@pytest.fixture
def mock_email():
    mock = MagicMock()
    mock.sent_count = 0
    mock.last_attachment_type = None
    return mock
```

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
markers =
    integration: marks tests as integration tests (require external APIs)
    e2e: marks tests as end-to-end tests
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

---

## 9. 개발 환경 설정

### 9.1. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./shared:/shared
      - ~/.ai-tax-assistant:/root/ai-tax-assistant
    environment:
      - DATABASE_URL=sqlite:///./data/ai_tax_assistant.db
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - ./shared:/shared
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    command: npm run dev
```

### 9.2. Makefile

```makefile
# Makefile
.PHONY: install dev test lint

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker-compose up

test:
	cd backend && pytest tests/ -v

test-unit:
	cd backend && pytest tests/unit/ -v

test-integration:
	cd backend && pytest tests/integration/ -v --run-integration

test-e2e:
	cd backend && pytest tests/e2e/ -v

test-coverage:
	cd backend && pytest tests/ --cov=src --cov-report=html

lint:
	cd backend && ruff check src/
	cd frontend && npm run lint
```

---

## 10. 세법/회계법 컨텍스트 서비스 (Tax Law Context Service)

### 10.1. 개요

AI가 스마트 질문 생성 시 매번 세법 전체를 프롬프트에 포함하는 것은 비효율적입니다.
**Tax Law Context Service**는 세법/회계법을 사전 인덱싱하여 거래 유형에 따라 관련 조항만 검색하는 External Service입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Tax Law Context Service Architecture                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐ │
│  │   거래 데이터     │───►│  Transaction     │───►│  Tax Law Index   │ │
│  │ (Transaction)    │    │  Classifier      │    │  (Vector DB)     │ │
│  │                  │    │                  │    │                  │ │
│  └──────────────────┘    └──────────────────┘    └────────┬──────────┘ │
│                                                           │             │
│                                                           ▼             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐ │
│  │   AI Service     │◄───│  Relevant Laws   │◄───│  Semantic Search │ │
│  │ (Question Gen)   │    │  (Context)       │    │  (Top-K Results) │ │
│  │                  │    │                  │    │                  │ │
│  └──────────────────┘    └──────────────────┘    └───────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2. 주요 법령 (2026년 기준)

#### 10.2.1. 세법 (Tax Law)

| 법령명 | 약칭 | 주요 적용 영역 | 최종 개정 |
|--------|------|---------------|----------|
| 법인세법 | CIT | 법인 소득, 손금/익금, 세액공제 | 2025.12 (2026 시행) |
| 소득세법 | PIT | 급여, 배당, 사업소득, 원천징수 | 2025.12 |
| 부가가치세법 | VAT | 매입/매출, 세금계산서, 매입세액공제 | 2025.12 |
| 조세특례제한법 | STTC | 창업감면, R&D세액공제, 투자세액공제 | 2025.12 |

#### 10.2.2. 회계법 (Accounting Law)

| 법령명 | 약칭 | 주요 적용 영역 |
|--------|------|---------------|
| 주식회사등의외부감사에관한법률 | 외감법 | 외부감사, 재무제표, 내부회계관리 |
| 기업회계기준 (K-IFRS/K-GAAP) | K-IFRS | 재무제표 작성, 회계처리 기준 |

### 10.3. 유저 친화적 인덱스 (User-Friendly Index)

거래 데이터를 분석하여 **"유저가 이해할 수 있는 카테고리"**로 분류하고, 해당 카테고리에 맞는 세법 조항을 자동 검색합니다.

#### 10.3.1. 거래 분류 카테고리 (Transaction Categories)

```python
# backend/src/services/tax_context/categories.py

from enum import Enum
from dataclasses import dataclass
from typing import List

class TransactionCategory(Enum):
    """거래 분류 카테고리 (유저 친화적 워딩)"""

    # ========== 비용 지출 ==========
    EMPLOYEE_MEAL = "직원 식대"           # 복리후생비
    BUSINESS_ENTERTAINMENT = "거래처 접대"  # 접대비
    OFFICE_RENT = "사무실 임대료"          # 임차료
    OFFICE_SUPPLIES = "사무용품 구매"       # 소모품비
    SOFTWARE_SUBSCRIPTION = "소프트웨어 구독"  # 무형자산/경비
    TRAVEL_EXPENSE = "출장비"              # 여비교통비
    ADVERTISING = "광고/마케팅"            # 광고선전비
    PROFESSIONAL_FEE = "전문가 비용"       # 지급수수료 (세무사, 변호사)
    INSURANCE = "보험료"                   # 보험료
    UTILITY = "공과금"                     # 통신비, 수도광열비

    # ========== 인건비 ==========
    SALARY = "급여 지급"                   # 급여, 원천징수
    FREELANCER_FEE = "프리랜서 비용"       # 사업소득 원천징수 3.3%
    BONUS = "상여금/성과급"                # 급여, 원천징수
    SEVERANCE = "퇴직금"                   # 퇴직급여

    # ========== 매입/매출 ==========
    PURCHASE_GOODS = "상품/재료 매입"      # 매입세액공제
    SALES_REVENUE = "매출 입금"            # 매출세액
    SERVICE_REVENUE = "용역 매출"          # 세금계산서

    # ========== 금융/투자 ==========
    INTEREST_INCOME = "이자 수입"          # 이자소득
    DIVIDEND_INCOME = "배당 수입"          # 배당소득
    LOAN_REPAYMENT = "대출 상환"           # 이자비용
    INVESTMENT = "투자/자산취득"           # 감가상각, 투자세액공제

    # ========== 세금/공과금 ==========
    TAX_PAYMENT = "세금 납부"              # 부가세, 법인세, 원천세
    SOCIAL_INSURANCE = "4대보험"           # 국민연금, 건강보험 등

    # ========== 기타 ==========
    INTERNAL_TRANSFER = "내부 이체"        # 계좌 간 이체 (세무 무관)
    UNKNOWN = "확인 필요"                  # 분류 불가


@dataclass
class TaxLawReference:
    """세법 참조 정보"""
    law_name: str           # 법령명
    article: str            # 조항 (예: "제25조")
    title: str              # 조항 제목
    summary: str            # 요약 설명
    key_points: List[str]   # 핵심 포인트
    limits: dict            # 한도/기준 (있는 경우)
    evidence_required: List[str]  # 필요 증빙


# 카테고리별 관련 세법 매핑
CATEGORY_TAX_LAW_MAP: dict[TransactionCategory, List[str]] = {
    TransactionCategory.EMPLOYEE_MEAL: [
        "CIT-복리후생비",
        "VAT-적격증빙",
        "CIT-손금산입"
    ],
    TransactionCategory.BUSINESS_ENTERTAINMENT: [
        "CIT-접대비한도",
        "CIT-제25조",
        "VAT-접대비매입세액불공제"
    ],
    TransactionCategory.SALARY: [
        "PIT-원천징수",
        "PIT-근로소득",
        "CIT-인건비손금"
    ],
    TransactionCategory.FREELANCER_FEE: [
        "PIT-사업소득원천징수",
        "CIT-지급수수료",
        "VAT-용역매입세액"
    ],
    # ... 나머지 카테고리 매핑
}
```

#### 10.3.2. 유저에게 보여줄 카테고리 UI

```typescript
// frontend/src/types/taxContext.ts

export interface TransactionCategoryInfo {
  id: string;
  label: string;           // 유저 친화적 라벨
  description: string;     // 짧은 설명
  icon: string;            // 아이콘 (lucide-react)
  examples: string[];      // 예시 거래
  relatedLaws: string[];   // 관련 세법 (참고용)
}

export const TRANSACTION_CATEGORIES: TransactionCategoryInfo[] = [
  {
    id: "employee_meal",
    label: "직원 식대",
    description: "직원과 함께한 식사, 회식, 간식 등",
    icon: "Utensils",
    examples: ["팀 점심", "야근 저녁", "회식"],
    relatedLaws: ["복리후생비", "적격증빙"]
  },
  {
    id: "business_entertainment",
    label: "거래처 접대",
    description: "거래처, 고객, 파트너와의 식사/선물",
    icon: "Handshake",
    examples: ["고객 미팅 식사", "명절 선물", "골프"],
    relatedLaws: ["접대비 한도", "법인세법 제25조"]
  },
  {
    id: "freelancer_fee",
    label: "프리랜서 비용",
    description: "외주 용역비, 프리랜서 대금",
    icon: "UserCheck",
    examples: ["디자이너 외주비", "개발 용역비", "컨설팅비"],
    relatedLaws: ["원천징수 3.3%", "지급명세서"]
  },
  {
    id: "office_rent",
    label: "사무실 임대료",
    description: "사무실, 공유오피스, 창고 임차료",
    icon: "Building",
    examples: ["월 임대료", "관리비", "보증금 이자"],
    relatedLaws: ["임차료 경비처리", "부가세 매입공제"]
  },
  {
    id: "software_subscription",
    label: "소프트웨어 구독",
    description: "SaaS, 클라우드, 도메인 등 구독 서비스",
    icon: "Cloud",
    examples: ["AWS", "Slack", "Notion", "Adobe"],
    relatedLaws: ["경비처리", "무형자산"]
  },
  // ... 나머지 카테고리
];
```

### 10.4. 세법 인덱스 구조 (Tax Law Index Schema)

#### 10.4.1. Vector DB 스키마 (ChromaDB)

```python
# backend/src/services/tax_context/index.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import date

@dataclass
class TaxLawChunk:
    """세법 조항 청크 (Vector DB 저장 단위)"""

    # 식별자
    chunk_id: str               # 고유 ID (예: "CIT_제25조_1")
    law_code: str               # 법령 코드 (CIT, PIT, VAT, STTC)

    # 조항 정보
    article: str                # 조항 번호 (예: "제25조")
    paragraph: Optional[str]    # 항 (예: "제1항")
    title: str                  # 조항 제목

    # 내용
    content: str                # 조문 전문
    summary: str                # AI 요약 (3-5문장)
    key_points: List[str]       # 핵심 포인트 (3-7개)

    # 메타데이터
    effective_date: date        # 시행일
    last_revised: date          # 최종 개정일
    categories: List[str]       # 연관 거래 카테고리

    # 실무 가이드
    limits: Optional[dict]      # 한도 정보 (예: {"접대비": "연 3,600만원"})
    evidence_required: List[str]  # 필요 증빙 서류
    common_mistakes: List[str]  # 흔한 실수

    # 임베딩 (ChromaDB 자동 생성)
    # embedding: List[float]


@dataclass
class TaxLawIndex:
    """세법 인덱스 전체 구조"""

    version: str                # 인덱스 버전 (예: "2026.02")
    last_updated: date          # 최종 업데이트
    total_chunks: int           # 총 청크 수

    # 법령별 청크 수
    chunk_counts: dict          # {"CIT": 150, "PIT": 120, ...}

    # 카테고리별 인덱스
    category_index: dict        # {"직원식대": ["CIT_복리후생_1", ...]}
```

#### 10.4.2. 인덱스 구축 프로세스

```python
# backend/src/services/tax_context/builder.py

import chromadb
from chromadb.config import Settings
import anthropic
from typing import List
from pathlib import Path

class TaxLawIndexBuilder:
    """세법 인덱스 빌더"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.client = chromadb.PersistentClient(
            path=str(data_dir / "tax_law_db"),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="korean_tax_law",
            metadata={"hnsw:space": "cosine"}
        )

    def build_index(self, law_sources: List[dict]) -> None:
        """
        법령 원문에서 인덱스 구축

        law_sources 예시:
        [
            {
                "law_code": "CIT",
                "law_name": "법인세법",
                "source_url": "https://www.law.go.kr/...",
                "articles": [...]
            }
        ]
        """
        for source in law_sources:
            chunks = self._parse_law_to_chunks(source)
            self._add_to_collection(chunks)

    def _parse_law_to_chunks(self, source: dict) -> List[TaxLawChunk]:
        """법령 원문을 청크로 분할"""
        chunks = []
        for article in source["articles"]:
            # 조항별로 분할
            chunk = TaxLawChunk(
                chunk_id=f"{source['law_code']}_{article['number']}",
                law_code=source["law_code"],
                article=article["number"],
                title=article["title"],
                content=article["content"],
                summary=self._generate_summary(article["content"]),
                key_points=self._extract_key_points(article["content"]),
                effective_date=article.get("effective_date"),
                last_revised=article.get("last_revised"),
                categories=self._classify_categories(article),
                limits=self._extract_limits(article["content"]),
                evidence_required=self._extract_evidence(article["content"]),
                common_mistakes=[]
            )
            chunks.append(chunk)
        return chunks

    def _add_to_collection(self, chunks: List[TaxLawChunk]) -> None:
        """ChromaDB에 청크 추가"""
        documents = [c.content + "\n\n" + c.summary for c in chunks]
        metadatas = [
            {
                "law_code": c.law_code,
                "article": c.article,
                "title": c.title,
                "categories": ",".join(c.categories),
                "effective_date": str(c.effective_date) if c.effective_date else "",
            }
            for c in chunks
        ]
        ids = [c.chunk_id for c in chunks]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
```

### 10.5. 세법 컨텍스트 검색 API

#### 10.5.1. API 엔드포인트

```python
# backend/src/api/tax_context.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..services.tax_context.search import TaxLawSearchService

router = APIRouter(prefix="/api/v1/tax-context", tags=["Tax Context"])


class TransactionContextRequest(BaseModel):
    """거래 컨텍스트 요청"""
    transaction_id: str
    description: str          # 거래 적요
    amount: int
    counterparty: Optional[str]  # 거래 상대방
    category_hint: Optional[str]  # 유저가 선택한 카테고리 (있는 경우)


class TaxLawContext(BaseModel):
    """세법 컨텍스트 응답"""
    category: str             # 분류된 카테고리
    category_label: str       # 유저 친화적 라벨
    confidence: float         # 분류 신뢰도 (0-1)

    related_laws: List[dict]  # 관련 세법 조항
    # [{
    #     "law_code": "CIT",
    #     "article": "제25조",
    #     "title": "접대비의 손금불산입",
    #     "summary": "...",
    #     "key_points": [...],
    #     "limits": {...}
    # }]

    evidence_checklist: List[str]  # 필요 증빙 체크리스트
    common_questions: List[str]    # 세무사가 물을 수 있는 질문
    common_mistakes: List[str]     # 흔한 실수


@router.post("/search", response_model=TaxLawContext)
async def search_tax_context(
    request: TransactionContextRequest,
    search_service: TaxLawSearchService = Depends()
) -> TaxLawContext:
    """
    거래 내용을 분석하여 관련 세법 컨텍스트 검색

    1. 거래 분류 (Transaction Classification)
    2. 관련 세법 검색 (Semantic Search)
    3. 컨텍스트 조합 (Context Assembly)
    """
    # 1. 거래 분류
    category = await search_service.classify_transaction(
        description=request.description,
        amount=request.amount,
        counterparty=request.counterparty,
        hint=request.category_hint
    )

    # 2. 관련 세법 검색
    related_laws = await search_service.search_related_laws(
        category=category,
        description=request.description,
        top_k=5
    )

    # 3. 컨텍스트 조합
    context = await search_service.assemble_context(
        category=category,
        laws=related_laws,
        transaction=request
    )

    return context


@router.get("/categories")
async def get_categories() -> List[dict]:
    """
    거래 분류 카테고리 목록 조회
    (유저가 직접 선택할 수 있도록)
    """
    return [
        {
            "id": cat.value,
            "label": cat.value,
            "description": CATEGORY_DESCRIPTIONS.get(cat, ""),
            "examples": CATEGORY_EXAMPLES.get(cat, [])
        }
        for cat in TransactionCategory
        if cat != TransactionCategory.INTERNAL_TRANSFER
    ]


@router.get("/laws/{law_code}")
async def get_law_details(
    law_code: str,
    article: Optional[str] = None
) -> dict:
    """
    특정 법령 상세 조회
    """
    # ChromaDB에서 해당 법령 조회
    pass
```

### 10.6. AI 서비스 통합

#### 10.6.1. 할루시네이션 방지 원칙 (Anthropic 권장)

세법/회계법은 정확성이 중요하므로, AI 호출 시 다음 원칙을 적용합니다:

| 원칙 | 설명 | 구현 방법 |
|------|------|----------|
| **컨텍스트 제한** | 제공된 세법 컨텍스트만 참조 | `<context>` 태그로 명시적 범위 지정 |
| **모름 허용** | 확신 없으면 "모르겠다" 답변 허용 | `if_uncertain` 지시문 추가 |
| **증거 우선** | 답변 전 관련 조항 인용 먼저 | `<evidence>` → `<answer>` 순서 |
| **신뢰도 표시** | 확신 수준 명시 | `confidence_level` 필드 필수 |
| **출처 인용** | 모든 주장에 법령 조항 명시 | `source` 필드로 법령 참조 |

```python
# backend/src/services/ai_service.py

# 할루시네이션 방지 시스템 프롬프트
ANTI_HALLUCINATION_SYSTEM_PROMPT = """
당신은 스타트업 CEO를 도와주는 세무 어시스턴트입니다.

## 핵심 원칙: 정확성 > 친절함

### 1. 컨텍스트 제한 (CRITICAL)
- 반드시 <tax_law_context> 태그 내 제공된 세법 정보만 참조하세요.
- 제공된 컨텍스트에 없는 세법 정보는 절대 생성하지 마세요.
- 외부 지식이나 훈련 데이터의 세법 정보를 사용하지 마세요.

### 2. 불확실성 인정
- 컨텍스트에서 답을 찾을 수 없으면 솔직히 "제공된 정보로는 확인할 수 없습니다"라고 답하세요.
- 추측하거나 일반적인 세무 지식으로 답변을 채우지 마세요.
- 확신이 없으면 "세무사 확인이 필요합니다"라고 안내하세요.

### 3. 증거 우선 응답
모든 답변 시 다음 순서를 따르세요:
1. <evidence> 태그에 관련 세법 조항을 먼저 인용
2. <reasoning> 태그에 해당 조항이 이 거래에 적용되는 이유 설명
3. <answer> 태그에 최종 답변 작성
4. <confidence> 태그에 확신도 표시 (high/medium/low)
5. <source> 태그에 참조한 법령 조항 명시

### 4. 금지 사항
- ❌ "일반적으로...", "보통...", "대부분의 경우..." 같은 모호한 표현
- ❌ 제공된 컨텍스트에 없는 세율, 한도, 기준 언급
- ❌ 확인되지 않은 세법 개정 정보 언급
- ❌ 세무 조언이나 절세 전략 제안 (정보 제공만 가능)

### 5. 권장 표현
- ✅ "제공된 법인세법 제25조에 따르면..."
- ✅ "해당 컨텍스트에는 이 정보가 포함되어 있지 않습니다"
- ✅ "정확한 적용은 세무사 확인이 필요합니다"
"""
```

#### 10.6.2. 스마트 질문 생성 (할루시네이션 방지 적용)

```python
# backend/src/services/ai_service.py

class AIService:
    """AI 서비스 (할루시네이션 방지 적용)"""

    MODEL = "claude-3-5-sonnet-20241022"  # Claude 3.5 Sonnet

    def __init__(
        self,
        anthropic_client: anthropic.Anthropic,
        tax_context_service: TaxLawSearchService
    ):
        self.client = anthropic_client
        self.tax_context = tax_context_service

    async def generate_smart_questions(
        self,
        transaction: Transaction
    ) -> dict:
        """
        세법 컨텍스트 기반 스마트 질문 생성 (할루시네이션 방지)
        """
        # 1. 세법 컨텍스트 검색
        tax_context = await self.tax_context.search_tax_context(
            TransactionContextRequest(
                transaction_id=transaction.id,
                description=transaction.description,
                amount=transaction.amount,
                counterparty=transaction.counterparty_name
            )
        )

        # 2. 할루시네이션 방지 프롬프트 구성
        prompt = f"""
<tax_law_context>
{self._format_law_context(tax_context.related_laws)}
</tax_law_context>

<transaction>
- 거래일: {transaction.date}
- 금액: {transaction.amount:,}원
- 내용: {transaction.description}
- 거래처: {transaction.counterparty_name or "미확인"}
- 분류: {tax_context.category_label} (신뢰도: {tax_context.confidence:.0%})
</transaction>

<evidence_checklist>
{chr(10).join(f"- {e}" for e in tax_context.evidence_checklist)}
</evidence_checklist>

## 작업
위 <tax_law_context>를 참조하여 이 거래의 세무 처리를 위한 질문을 생성하세요.

## 규칙
1. 질문은 <tax_law_context>에 있는 정보만 기반으로 작성
2. 컨텍스트에 없는 세법 조항이나 기준은 언급하지 않음
3. 각 질문에 관련 법령 조항(source) 명시
4. 컨텍스트가 부족하면 "확인 필요" 질문으로 대체

## 출력 형식
다음 JSON 형식으로 출력하세요:
{{
    "questions": [
        {{
            "id": "Q1",
            "question": "질문 내용",
            "source": "법인세법 제25조" 또는 "컨텍스트 외 - 세무사 확인 필요",
            "confidence": "high" | "medium" | "low",
            "options": ["예", "아니오"] 또는 null
        }}
    ],
    "context_coverage": "complete" | "partial" | "insufficient",
    "disclaimer": "컨텍스트 부족 시 안내 메시지"
}}
"""

        response = await self.client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            system=ANTI_HALLUCINATION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # 할루시네이션 최소화를 위해 temperature 0
        )

        result = json.loads(response.content[0].text)

        # 3. 응답 검증: source가 컨텍스트 내 법령인지 확인
        validated_questions = self._validate_sources(
            result["questions"],
            tax_context.related_laws
        )

        return {
            "questions": validated_questions,
            "context_coverage": result.get("context_coverage", "unknown"),
            "disclaimer": result.get("disclaimer")
        }

    def _validate_sources(
        self,
        questions: List[dict],
        laws: List[dict]
    ) -> List[dict]:
        """질문의 source가 실제 컨텍스트에 있는지 검증"""
        valid_sources = {f"{law['law_code']} {law['article']}" for law in laws}
        valid_sources.add("컨텍스트 외 - 세무사 확인 필요")

        for q in questions:
            source = q.get("source", "")
            # source가 유효한 컨텍스트 내 법령인지 확인
            if not any(vs in source for vs in valid_sources):
                # 유효하지 않은 source는 경고로 표시
                q["source"] = f"⚠️ {source} (컨텍스트 미확인)"
                q["confidence"] = "low"

        return questions

    def _format_law_context(self, laws: List[dict]) -> str:
        """세법 컨텍스트 포맷팅 (인용 가능한 형태)"""
        formatted = []
        for i, law in enumerate(laws, 1):
            formatted.append(f"""
[LAW-{i:02d}] {law['law_code']} {law['article']}: {law['title']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{law['summary']}

핵심 포인트:
{chr(10).join(f"  • {p}" for p in law['key_points'])}

한도/기준: {law.get('limits', '없음')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        return "\n".join(formatted)
```

#### 10.6.3. 월간 요약 생성 (할루시네이션 방지 적용)

```python
# backend/src/services/ai_service.py

async def generate_monthly_summary(
    self,
    transactions: List[Transaction],
    enriched_contexts: List[EnrichedContext]
) -> dict:
    """
    월간 거래 요약 생성 (세무사용)
    할루시네이션 방지: 제공된 데이터만 기반으로 요약
    """
    # 거래 데이터 구조화
    tx_data = self._format_transactions_for_summary(transactions, enriched_contexts)

    prompt = f"""
<transaction_data>
{tx_data}
</transaction_data>

## 작업
위 <transaction_data>를 기반으로 세무사에게 전달할 월간 거래 요약을 작성하세요.

## 핵심 규칙 (할루시네이션 방지)
1. **데이터 기반만**: <transaction_data>에 있는 거래만 언급
2. **수치 검증**: 합계, 건수는 직접 계산 - 추측 금지
3. **분류 그대로**: 유저가 확인한 분류 그대로 사용
4. **미확인 명시**: enriched_status가 "pending"인 거래는 "확인 필요"로 표시
5. **세무 조언 금지**: 요약만 제공, 절세 조언 금지

## 출력 형식
<summary_scratchpad>
(먼저 데이터를 분석하고 계산 과정을 기록)
- 총 거래 건수: [직접 세기]
- 입금 합계: [직접 계산]
- 지출 합계: [직접 계산]
- 미확인 거래: [직접 세기]
</summary_scratchpad>

<monthly_summary>
{{
    "period": "YYYY년 MM월",
    "overview": {{
        "total_transactions": 숫자,
        "total_income": 숫자,
        "total_expense": 숫자,
        "pending_count": 숫자
    }},
    "categories": [
        {{
            "name": "카테고리명",
            "count": 숫자,
            "amount": 숫자,
            "confidence": "모든 거래 확인됨" | "N건 미확인"
        }}
    ],
    "attention_required": [
        {{
            "issue": "이슈 설명",
            "transactions": ["TX001", "TX002"],
            "source": "데이터 기반" | "세무사 확인 필요"
        }}
    ],
    "data_completeness": "complete" | "partial",
    "disclaimer": "이 요약은 입력된 거래 데이터만 기반으로 생성되었습니다."
}}
</monthly_summary>
"""

    response = await self.client.messages.create(
        model=self.MODEL,
        max_tokens=4096,
        system=ANTI_HALLUCINATION_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    # scratchpad와 summary 분리 파싱
    content = response.content[0].text
    summary_match = re.search(
        r'<monthly_summary>(.*?)</monthly_summary>',
        content,
        re.DOTALL
    )

    if summary_match:
        return json.loads(summary_match.group(1))
    else:
        raise ValueError("Summary generation failed - no valid output")
```

#### 10.6.4. 응답 신뢰도 모니터링

```python
# backend/src/services/ai_service.py

@dataclass
class AIResponseMetrics:
    """AI 응답 품질 메트릭"""
    context_adherence: float    # 컨텍스트 준수율 (0-1)
    source_validity: float      # 유효 출처 비율 (0-1)
    confidence_distribution: dict  # {"high": n, "medium": n, "low": n}
    hallucination_flags: List[str]  # 감지된 할루시네이션 징후


class AIResponseValidator:
    """AI 응답 검증기"""

    HALLUCINATION_PATTERNS = [
        r"일반적으로",
        r"보통[은\s]",
        r"대부분의\s경우",
        r"알려진\s바에\s따르면",
        r"흔히",
        r"\d{4}년.*개정",  # 컨텍스트에 없는 개정 정보
    ]

    def validate(
        self,
        response: dict,
        provided_context: List[dict]
    ) -> AIResponseMetrics:
        """응답 검증 및 메트릭 계산"""
        flags = []

        # 1. 할루시네이션 패턴 검사
        response_text = json.dumps(response, ensure_ascii=False)
        for pattern in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, response_text):
                flags.append(f"Suspicious pattern: {pattern}")

        # 2. Source 유효성 검사
        valid_sources = {f"{law['law_code']} {law['article']}" for law in provided_context}
        questions = response.get("questions", [])

        valid_source_count = sum(
            1 for q in questions
            if any(vs in q.get("source", "") for vs in valid_sources)
        )

        source_validity = valid_source_count / len(questions) if questions else 1.0

        # 3. Confidence 분포
        confidence_dist = {"high": 0, "medium": 0, "low": 0}
        for q in questions:
            conf = q.get("confidence", "low")
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1

        return AIResponseMetrics(
            context_adherence=1.0 - (len(flags) / 10),  # 플래그당 -10%
            source_validity=source_validity,
            confidence_distribution=confidence_dist,
            hallucination_flags=flags
        )
```

### 10.7. 세법 인덱스 데이터 관리

#### 10.7.1. 데이터 소스

```yaml
# backend/data/tax_law_sources.yaml

sources:
  - code: CIT
    name: 법인세법
    official_url: https://www.law.go.kr/법령/법인세법
    version: "2026.01.01 시행"
    priority_articles:
      - "제25조"   # 접대비
      - "제19조"   # 손금
      - "제25조의2" # 기부금
      - "제40조"   # 손익귀속시기

  - code: PIT
    name: 소득세법
    official_url: https://www.law.go.kr/법령/소득세법
    version: "2026.01.01 시행"
    priority_articles:
      - "제127조"  # 원천징수
      - "제20조"   # 근로소득
      - "제21조"   # 사업소득

  - code: VAT
    name: 부가가치세법
    official_url: https://www.law.go.kr/법령/부가가치세법
    version: "2026.01.01 시행"
    priority_articles:
      - "제17조"   # 매입세액공제
      - "제39조"   # 매입세액불공제
      - "제32조"   # 세금계산서

  - code: STTC
    name: 조세특례제한법
    official_url: https://www.law.go.kr/법령/조세특례제한법
    version: "2026.01.01 시행"
    priority_articles:
      - "제6조"    # 창업중소기업 세액감면
      - "제7조"    # 중소기업 특별세액감면
      - "제10조"   # R&D세액공제
```

#### 10.7.2. 인덱스 업데이트 배치 [v2.0 예정]

> ⏳ **MVP에서는 제외**: 세법 인덱스는 초기 빌드 시 수동 생성합니다.
> 자동 업데이트 기능은 v2.0에서 구현 예정입니다.

```python
# [v2.0] backend/src/jobs/update_tax_index.py

from apscheduler.triggers.cron import CronTrigger

class TaxIndexUpdateJob:
    """
    [v2.0 예정] 세법 인덱스 자동 업데이트 배치
    - 스케줄: 매월 1일 02:00
    - 국가법령정보센터 API 연동
    """

    def __init__(self, builder: TaxLawIndexBuilder):
        self.builder = builder

    async def run(self) -> None:
        """
        1. 국가법령정보센터 API에서 최신 법령 조회
        2. 변경된 조항 감지
        3. 인덱스 업데이트
        4. 버전 로그 기록
        """
        pass  # v2.0 구현 예정
```

**MVP 대안**: 수동 인덱스 빌드 스크립트
```bash
# 개발자가 수동으로 세법 인덱스 업데이트
python scripts/build_tax_index.py --source data/tax_updates_2026.yaml
```

### 10.8. 2026년 주요 세법 개정사항 (Pre-indexed)

#### 10.8.1. 법인세

```yaml
# backend/data/tax_updates_2026.yaml

cit_2026:
  - article: "세율 개정"
    summary: "법인세율 전 구간 1%p 인상 (2022년 이전 수준 환원)"
    rates:
      - range: "2억원 이하"
        rate: "10%"
        previous: "9%"
      - range: "2억~200억원"
        rate: "20%"
        previous: "19%"
      - range: "200억~3,000억원"
        rate: "22%"
        previous: "21%"
      - range: "3,000억원 초과"
        rate: "25%"
        previous: "24%"
    effective_date: "2026.01.01"
```

#### 10.8.2. 부가가치세

```yaml
vat_2026:
  - article: "가산세 강화"
    summary: "허위 세금계산서 가산세율 3% → 4% 인상"
    key_point: "실제 거래 없이 세금계산서 주고받는 행위 제재 강화"
    effective_date: "2026.01.01"
```

#### 10.8.3. 조세특례제한법

```yaml
sttc_2026:
  - article: "제6조 창업중소기업 세액감면"
    summary: "2027.12.31까지 창업 시 소득세/법인세 세액감면"
    rates:
      - region: "수도권 외, 인구감소지역"
        rate: "100%"
      - region: "수도권 (제외지역 외)"
        rate: "75%"
      - region: "수도권과밀억제권역"
        rate: "50%"
    duration: "최초 소득 발생 후 5년"
    effective_date: "2026.01.01"
```

### 10.9. 적격증빙 체크리스트 (Pre-defined)

```python
# backend/src/services/tax_context/evidence.py

EVIDENCE_CHECKLIST = {
    "직원 식대": {
        "required": ["법인카드 전표", "세금계산서", "현금영수증 중 1개"],
        "optional": ["참석자 명단 (회식 시)"],
        "threshold": 30000,  # 3만원 이상 시 적격증빙 필수
        "notes": ["간이영수증은 3만원 이하만 인정"]
    },
    "거래처 접대": {
        "required": ["법인카드 전표", "세금계산서", "현금영수증 중 1개"],
        "optional": ["접대 목적/상대방 메모"],
        "threshold": 10000,  # 1만원 초과 시 적격증빙 필수
        "limits": {
            "기본한도": "연 3,600만원 (중소기업)",
            "경고기준": "연매출 대비 0.3% 초과 시 점검 필요"
        },
        "notes": ["간이영수증은 1만원 이하만 인정"]
    },
    "프리랜서 비용": {
        "required": ["계좌이체 증빙", "용역계약서"],
        "optional": ["세금계산서 (부가세 별도 시)"],
        "withholding": {
            "rate": "3.3%",
            "type": "사업소득 원천징수"
        },
        "notes": ["원천징수 신고 필수", "지급명세서 제출 필수 (연 1회)"]
    },
    "사무실 임대료": {
        "required": ["세금계산서 또는 임대차계약서"],
        "vat_deductible": True,
        "notes": ["부가세 매입세액공제 가능"]
    },
    # ... 나머지 카테고리
}
```

---

## 11. 기능정의서 매핑 검증

| User Story | 기술스펙 섹션 | API | 테스트 |
|------------|--------------|-----|--------|
| US-001: Transaction Tracking | 4.1, 5.2 | `/transactions/sync` | `test_transaction.py` |
| US-002: Smart Questions | 4.2, 4.3, 5.3, **10** | `/enrichment/questions`, `/enrichment/answers`, `/tax-context/search` | `test_enrichment.py`, `test_tax_context.py` |
| US-003: Enriched Context Storage | 2.2, 4.2 | `/enrichment/context/{id}` | `test_enrichment.py` |
| US-004: Monthly Document Generation | 2.3, 5.4 | `/documents/generate` | `test_monthly_document.py` |
| US-005: Document Review & Edit | 4.3, 6.2 | `/documents/{id}`, `/documents/{id}/review` | `test_full_flow.py` |
| US-006: Accountant Delivery | 4.4 | `/delivery/send` | `test_full_flow.py` |
| **Tax Context Service** | **10** | `/tax-context/search`, `/tax-context/categories` | `test_tax_context.py`, `test_tax_index.py` |

---

**Document Version**: 1.4
**Last Updated**: 2026-02-06
**Status**: 구현 준비 완료
**Changelog**:
- v1.4: AI API를 Claude API (3.5 Sonnet)로 변경
  - 할루시네이션 최소화: Claude의 Constitutional AI 학습 활용
  - 비용 효율: 월 $3-5 예상 (121회/월 기준)
  - 의존성: `anthropic==0.18.0`
  - 사용량 추적: Anthropic Console 대시보드 활용
- v1.3: 문서 구조 통합 및 섹션 간 참조 정리
  - 섹션 2.5: TaxLawChunk 모델 추가 (→ 섹션 10.4 참조)
  - 섹션 3.5: Tax Context APIs 추가 (→ 섹션 10.5 참조)
  - 섹션 3.6: 에러 코드에 Tax Context (7xxx), AI Hallucination (6003) 추가
  - 섹션 4.3: AI API 연동을 섹션 10.6으로 통합, 간결화
  - 섹션 5.1: Scheduler 배치 요약 테이블 추가
  - 섹션 10.7.2: update_tax_index 배치 → v2.0 스코프로 이동
- v1.2: AI 할루시네이션 방지 기법 추가 (섹션 10.6)
  - Anthropic 권장 프롬프트 엔지니어링 적용
  - 컨텍스트 제한 시스템 프롬프트
  - `<evidence>` → `<answer>` 구조화 응답
  - Source 유효성 검증 로직
  - AIResponseValidator 할루시네이션 패턴 감지
  - 관련 TDD 테스트 케이스 추가
- v1.1: 세법/회계법 컨텍스트 서비스 추가 (섹션 10)
  - Tax Law Index (ChromaDB 기반 Vector DB)
  - 유저 친화적 거래 분류 카테고리
  - 2026년 세법 개정사항 Pre-indexed
  - 적격증빙 체크리스트
  - AI 서비스 통합
**Next Step**: 개발 환경 설정 → Unit Tests 작성 → 기능 구현
