# AI Tax Assistant

> 월말 문서 작업 10시간 → 10분

AI 세무 어시스턴트는 스타트업 CEO를 위한 세무 문서 자동화 도구입니다.

## 주요 기능

- **US-001**: 거래 내역 자동 수집 (팝빌 API)
- **US-002**: 세법 기반 스마트 질문 (Slack)
- **US-003**: 맥락 정보 저장
- **US-004**: 월말 문서 자동 생성
- **US-005**: 문서 리뷰 및 수정 (Web Dashboard)
- **US-006**: 세무사 이메일 전달

## 기술 스택

**Backend**
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- SQLite

**Frontend**
- Next.js 14
- TypeScript
- TailwindCSS
- React Query

**External APIs**
- Popbill (은행 거래 조회)
- Slack (알림)
- Claude API (AI 질문/요약)

## 시작하기

### 1. 필수 요구사항

- Python 3.11+
- Node.js 20+
- pip
- npm

### 2. 설치

```bash
# 프로젝트 디렉토리로 이동
cd ai-tax-assistant

# 모든 의존성 설치
make install

# 또는 수동 설치
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

### 3. 환경 설정

```bash
# 환경 변수 파일 생성
cp backend/.env.example backend/.env

# .env 파일을 열어 API 키 입력
# - SLACK_BOT_TOKEN
# - ANTHROPIC_API_KEY
# (Popbill, SMTP는 선택사항 - mock 사용 가능)
```

### 4. 실행

```bash
# 백엔드 서버 실행 (http://localhost:8000)
make dev-backend

# 다른 터미널에서 프론트엔드 실행 (http://localhost:3000)
make dev-frontend

# 또는 동시 실행
make dev
```

### 5. API 문서

서버 실행 후 Swagger UI에서 API 확인:
- http://localhost:8000/docs

## 개발

### 테스트

```bash
# 모든 테스트 실행
make test

# 커버리지 포함
make test-cov
```

### 코드 포맷팅

```bash
# 코드 스타일 검사
make lint

# 자동 포맷팅
make format
```

### 데이터베이스

```bash
# 데이터베이스 초기화
make db-init

# 데이터베이스 리셋
make db-reset
```

## 프로젝트 구조

```
ai-tax-assistant/
├── backend/                 # Python FastAPI
│   ├── src/
│   │   ├── api/            # API 라우터
│   │   ├── models/         # SQLAlchemy 모델
│   │   ├── services/       # 비즈니스 로직
│   │   ├── jobs/           # 배치 작업
│   │   └── utils/          # 유틸리티
│   ├── tests/              # 테스트
│   └── data/               # 데이터베이스 파일
├── frontend/               # Next.js
│   ├── src/
│   │   ├── app/           # App Router
│   │   ├── components/    # UI 컴포넌트
│   │   ├── hooks/         # React 훅
│   │   └── lib/           # 유틸리티
├── shared/                 # 공유 타입
└── Makefile               # 개발 명령어
```

## 라이선스

Private - All rights reserved
