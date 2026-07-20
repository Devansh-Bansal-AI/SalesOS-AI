# ============================================================
# SalesOS AI — Makefile
# ============================================================

.PHONY: help dev up down build migrate seed test lint format clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ──────────────────────────────────────────────────

up: ## Start all services
	docker compose -f docker/docker-compose.yml up -d

down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

build: ## Rebuild all containers
	docker compose -f docker/docker-compose.yml build

logs: ## Tail logs for all services
	docker compose -f docker/docker-compose.yml logs -f

# ── Backend ─────────────────────────────────────────────────

dev-backend: ## Run backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

seed: ## Seed database with sample data
	cd backend && python -m scripts.seed_db

# ── Frontend ────────────────────────────────────────────────

dev-frontend: ## Run frontend dev server
	cd frontend && npm run dev

# ── Testing ─────────────────────────────────────────────────

test: ## Run all tests
	cd backend && pytest -v

test-unit: ## Run unit tests
	cd backend && pytest tests/unit/ -v

test-integration: ## Run integration tests
	cd backend && pytest tests/integration/ -v

test-cov: ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html -v

# ── Code Quality ────────────────────────────────────────────

lint: ## Lint backend code
	cd backend && ruff check app/
	cd frontend && npx eslint src/

format: ## Format backend code
	cd backend && ruff format app/

typecheck: ## Run type checking
	cd backend && mypy app/
	cd frontend && npx tsc --noEmit

# ── Utilities ───────────────────────────────────────────────

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
