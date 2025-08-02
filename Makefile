# FIT File Mapper Development Makefile
# Uses UV for fast Python package management

.PHONY: help install install-dev install-all clean test lint format check
.PHONY: services-up services-down services-build services-logs
.PHONY: dev-setup precommit database-init

# Default target
help:
	@echo "FIT File Mapper Development Commands"
	@echo "====================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install       Install core dependencies"
	@echo "  install-dev   Install with development dependencies"
	@echo "  install-all   Install all optional dependencies"
	@echo "  dev-setup     Complete development environment setup"
	@echo ""
	@echo "Development Commands:"
	@echo "  test          Run all tests"
	@echo "  lint          Run linting (ruff + mypy)"
	@echo "  format        Format code (black + ruff)"
	@echo "  check         Run all checks (lint + test)"
	@echo "  precommit     Setup pre-commit hooks"
	@echo ""
	@echo "Services Commands:"
	@echo "  services-up   Start all services with docker-compose"
	@echo "  services-down Stop all services"
	@echo "  services-build Build service containers"
	@echo "  services-logs Show service logs"
	@echo ""
	@echo "Database Commands:"
	@echo "  database-init Initialize DuckDB database"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean         Clean up build artifacts and cache"

# Environment setup
install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

install-all:
	uv pip install -e ".[dev,advanced,web,all]"

# Complete development setup
dev-setup: install-all precommit database-init
	@echo "Development environment setup complete!"
	@echo "You can now run 'make services-up' to start all services"

# Pre-commit hooks
precommit:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Code quality
format:
	black src/ shared/ services/ tests/
	ruff check --fix src/ shared/ services/ tests/

lint:
	ruff check src/ shared/ services/ tests/
	mypy src/ shared/ services/

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov=shared --cov=services --cov-report=html --cov-report=term

# Combined checks
check: lint test

# Database operations
database-init:
	@echo "Initializing DuckDB database..."
	@mkdir -p database
	@python -c "from shared.database import WorkoutDatabase; db = WorkoutDatabase(); print('Database initialized successfully')"

# Docker services
services-build:
	@echo "Building optimized containers with multi-stage builds..."
	docker-compose -f .devcontainer/docker-compose.yml build --no-cache

services-build-dev:
	@echo "Building development containers..."
	docker-compose -f .devcontainer/docker-compose.yml build

services-up:
	docker-compose -f .devcontainer/docker-compose.yml up -d
	@echo "Services started:"
	@echo "  - API Gateway: http://localhost:8000"
	@echo "  - FIT Parser: http://localhost:8001"
	@echo "  - Map Service: http://localhost:8002"
	@echo "  - Visualization: http://localhost:8003"

services-down:
	docker-compose -f .devcontainer/docker-compose.yml down

services-logs:
	docker-compose -f .devcontainer/docker-compose.yml logs -f

services-restart: services-down services-up

# Production-ready builds
services-build-prod:
	@echo "Building production-optimized containers..."
	docker-compose -f .devcontainer/docker-compose.yml build --target production

services-size:
	@echo "Container sizes:"
	@docker images fit-file-mapper* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Development workflow shortcuts
dev-start: services-up
	@echo "Development environment started!"
	@echo "Visit http://localhost:8000/docs for API documentation"

dev-stop: services-down

# Service-specific commands
fit-parser:
	cd services/fit-parser && python main.py

map-service:
	cd services/map-service && python main.py

visualization:
	cd services/visualization && python main.py

api-gateway:
	cd services/api-gateway && python main.py

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/

# UV-specific commands
uv-lock:
	uv pip compile pyproject.toml -o requirements.lock

uv-upgrade:
	uv pip install --upgrade -e ".[dev,all]"

uv-sync:
	uv pip sync requirements.lock

# Data operations
sample-data:
	@echo "Setting up sample FIT files..."
	@mkdir -p data/fit_files/samples
	@echo "Place your sample FIT files in data/fit_files/samples/"

preload-nyc:
	curl -X POST http://localhost:8000/api/maps/preload-nyc

# Documentation
docs-serve:
	@echo "Serving documentation..."
	@echo "Open docs/development_roadmap.md for implementation guide"
	@echo "Open docs/example_usage.py for usage examples"

# Health checks
health:
	curl -s http://localhost:8000/api/health | python -m json.tool

# Quick development workflow
quick-start: dev-setup services-up
	@echo ""
	@echo "🚀 FIT File Mapper is ready for development!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Place FIT files in data/fit_files/"
	@echo "2. Visit http://localhost:8000/docs for API documentation"
	@echo "3. Upload a FIT file via POST /api/upload-fit"
	@echo "4. Create visualizations via the API"
	@echo ""
	@echo "Happy coding! 🗺️🏃‍♂️"

# Git hooks and workflow
git-setup:
	git config core.hooksPath .githooks
	chmod +x .githooks/*

# Performance monitoring
monitor:
	@echo "Service health status:"
	@make health
	@echo ""
	@echo "Database status:"
	@ls -la database/ 2>/dev/null || echo "Database not initialized"

# Backup and restore
backup-db:
	@mkdir -p backups
	@cp database/workouts.duckdb backups/workouts_$(shell date +%Y%m%d_%H%M%S).duckdb
	@echo "Database backed up to backups/"

restore-db:
	@echo "Available backups:"
	@ls -la backups/*.duckdb 2>/dev/null || echo "No backups found"
