.PHONY: help install test lint format clean run-tests coverage docs serve api-test validate-config

# Default target
help:
	@echo "WriterAI/Prometheus Novel Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install dependencies with Poetry"
	@echo "  make setup         - Full development setup"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-int      - Run integration tests"
	@echo "  make test-e2e      - Run end-to-end tests"
	@echo "  make coverage      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linting checks (ruff)"
	@echo "  make format        - Format code with ruff"
	@echo "  make typecheck     - Run type checking (mypy)"
	@echo "  make check-all     - Run all quality checks"
	@echo ""
	@echo "Development:"
	@echo "  make clean         - Clean temporary files"
	@echo "  make docs          - Build documentation"
	@echo "  make new-project   - Create new novel project (interactive)"
	@echo ""
	@echo "User Interfaces:"
	@echo "  make serve         - Start API v2.0 (port 8000)"
	@echo "  make serve-web     - Start Web Dashboard (port 8080)"
	@echo "  make dashboard     - Alias for serve-web"
	@echo ""
	@echo "Project Management:"
	@echo "  make list          - List all novel projects"
	@echo "  make generate      - Generate novel (requires CONFIG=path)"
	@echo "  make compile       - Compile novel (requires CONFIG=path)"

# Installation
install:
	cd prometheus_novel && poetry install

setup: install
	@echo "Setting up development environment..."
	@mkdir -p prometheus_novel/data prometheus_novel/logs prometheus_novel/output
	@echo "✅ Development environment ready!"

# Testing
test:
	cd prometheus_novel && poetry run pytest tests/ -v

test-unit:
	cd prometheus_novel && poetry run pytest tests/unit/ -v -m unit

test-int:
	cd prometheus_novel && poetry run pytest tests/integration/ -v -m integration

test-e2e:
	cd prometheus_novel && poetry run pytest tests/e2e/ -v -m e2e

test-fast:
	cd prometheus_novel && poetry run pytest tests/ -v -m "not slow"

coverage:
	cd prometheus_novel && poetry run pytest tests/ --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in prometheus_novel/htmlcov/index.html"

# Code Quality
lint:
	cd prometheus_novel && poetry run ruff check .

format:
	cd prometheus_novel && poetry run ruff check --fix .
	cd prometheus_novel && poetry run ruff format .

typecheck:
	cd prometheus_novel && poetry run mypy prometheus_lib/ stages/ interfaces/ --ignore-missing-imports

check-all: lint typecheck test-fast

# Cleaning
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Documentation
docs:
	@echo "Building documentation..."
	@echo "TODO: Add documentation build process"

# Project Management
new-project:
	cd prometheus_novel && python prometheus new --interactive

list:
	cd prometheus_novel && python prometheus list

generate:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG variable required. Usage: make generate CONFIG=configs/my_novel.yaml"; \
		exit 1; \
	fi
	cd prometheus_novel && python prometheus generate --config $(CONFIG) --all

compile:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG variable required. Usage: make compile CONFIG=configs/my_novel.yaml"; \
		exit 1; \
	fi
	cd prometheus_novel && python prometheus compile --config $(CONFIG)

# Quick operations
quick-test: format lint test-fast
	@echo "✅ Quick checks passed!"

pre-commit: format lint typecheck test-unit
	@echo "✅ Pre-commit checks passed!"

# Development server (if API is available)
serve:
	@echo "🚀 Starting WriterAI API v2.0..."
	cd prometheus_novel && poetry run uvicorn interfaces.api.app:app --reload --port 8000

serve-old:
	@echo "Starting legacy API..."
	cd prometheus_novel && poetry run uvicorn api:app --reload --port 8001

serve-web:
	@echo "🎨 Starting Beautiful Web Dashboard..."
	@echo "📱 Open: http://localhost:8080"
	cd prometheus_novel && poetry run uvicorn interfaces.web.app:app --reload --port 8080

dashboard:
	@$(MAKE) serve-web

# Database operations
db-init:
	@echo "Initializing ideas database..."
	cd prometheus_novel && python prometheus_lib/utils/ideas_db.py init

db-import:
	@echo "Importing ideas from ideas.txt..."
	cd prometheus_novel && python prometheus_lib/utils/ideas_db.py import ideas.txt

db-stats:
	@echo "Showing database statistics..."
	cd prometheus_novel && python prometheus_lib/utils/ideas_db.py stats

db-search:
	@if [ -z "$(QUERY)" ]; then \
		echo "Error: QUERY variable required. Usage: make db-search QUERY='your search'"; \
		exit 1; \
	fi
	cd prometheus_novel && python prometheus_lib/utils/ideas_db.py search "$(QUERY)"

# Example project creation
example:
	@echo "Creating example project..."
	@echo "Title: The Last Starship\nGenre: Sci-Fi\nSynopsis: A test novel about space exploration." | \
		cd prometheus_novel && python prometheus new --from-text --auto-confirm

# Watch for changes and run tests
watch:
	@echo "Watching for changes..."
	@echo "Install pytest-watch: pip install pytest-watch"
	cd prometheus_novel && ptw -- tests/

# Pre-commit hooks
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	cd prometheus_novel && poetry run pre-commit install
	@echo "✅ Pre-commit hooks installed"

pre-commit-run:
	@echo "Running pre-commit on all files..."
	cd prometheus_novel && poetry run pre-commit run --all-files

# Configuration validation
validate-config:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG variable required. Usage: make validate-config CONFIG=configs/my_novel.yaml"; \
		exit 1; \
	fi
	@echo "Validating configuration..."
	cd prometheus_novel && python prometheus_lib/utils/config_validator.py validate $(CONFIG)

# API testing
api-test:
	@echo "Testing API endpoints..."
	@echo "Make sure API is running: make serve"
	@echo "Then run: make api-test-requests"

api-test-requests:
	@echo "Testing API health endpoint..."
	curl -X GET http://localhost:8000/api/v2/health | jq

