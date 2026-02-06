"""
FastAPI application entry point.

AI Tax Assistant - 월말 문서 작업 10시간 → 10분
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import api_router
from src.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Starting AI Tax Assistant...")
    await init_db()
    print("✅ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down AI Tax Assistant...")
    await close_db()
    print("✅ Database connections closed")


app = FastAPI(
    title="AI Tax Assistant",
    description="""
    AI 세무 어시스턴트 - 월말 문서 작업 10시간 → 10분

    ## Features
    - **US-001**: Transaction Tracking (거래 내역 자동 수집)
    - **US-002**: Smart Questions (세법 기반 스마트 질문)
    - **US-003**: Enriched Context (맥락 정보 저장)
    - **US-004**: Monthly Document (월말 문서 자동 생성)
    - **US-005**: Document Review (문서 리뷰 및 수정)
    - **US-006**: Accountant Delivery (세무사 전달)
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "app": "AI Tax Assistant",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
