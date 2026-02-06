# AI Tax Assistant - Development Commands
.PHONY: install install-backend install-frontend dev dev-backend dev-frontend test lint format clean

# === Installation ===

install: install-backend install-frontend
	@echo "✅ All dependencies installed"

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Frontend dependencies installed"

# === Development ===

dev:
	@echo "🚀 Starting development servers..."
	@make dev-backend & make dev-frontend

dev-backend:
	@echo "🐍 Starting FastAPI server on http://localhost:8000"
	cd backend && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "⚛️ Starting Next.js server on http://localhost:3000"
	cd frontend && npm run dev

# === Testing ===

test:
	@echo "🧪 Running all tests..."
	cd backend && pytest

test-unit:
	@echo "🧪 Running unit tests..."
	cd backend && pytest tests/unit -v

test-integration:
	@echo "🧪 Running integration tests..."
	cd backend && pytest tests/integration -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	cd backend && pytest --cov=src --cov-report=html

# === Code Quality ===

lint:
	@echo "🔍 Linting code..."
	cd backend && python -m black --check src tests
	cd backend && python -m isort --check-only src tests
	cd backend && python -m mypy src

format:
	@echo "✨ Formatting code..."
	cd backend && python -m black src tests
	cd backend && python -m isort src tests

# === Database ===

db-init:
	@echo "🗄️ Initializing database..."
	cd backend && python -c "import asyncio; from src.database import init_db; asyncio.run(init_db())"
	@echo "✅ Database initialized"

db-reset:
	@echo "⚠️ Resetting database..."
	rm -f backend/data/ai_tax_assistant.db
	make db-init
	@echo "✅ Database reset"

# === Cleanup ===

clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# === Help ===

help:
	@echo "AI Tax Assistant - Available Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install all dependencies"
	@echo "  make install-backend  - Install backend dependencies"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start both backend and frontend"
	@echo "  make dev-backend      - Start backend only (FastAPI)"
	@echo "  make dev-frontend     - Start frontend only (Next.js)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Check code style"
	@echo "  make format           - Format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init          - Initialize database"
	@echo "  make db-reset         - Reset database"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove generated files"
