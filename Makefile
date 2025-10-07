.PHONY: help venv install install-dev authorize run test lint format docker-build docker-up docker-down docker-logs clean

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help:
	@echo "Available commands:"
	@echo "  make venv         - Create virtual environment"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make authorize    - Authorize Telegram session (run before docker-up)"
	@echo "  make run          - Run the bot locally"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code with black and isort"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start bot with Docker Compose"
	@echo "  make docker-down  - Stop bot"
	@echo "  make docker-logs  - View bot logs"
	@echo "  make clean        - Clean up cache files"

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt

install-dev: venv
	$(PIP) install -r requirements-dev.txt

authorize: venv
	$(PYTHON) scripts/authorize_session.py

run:
	$(PYTHON) main.py

test:
	$(PYTHON) -m pytest tests/ -v --cov=bot --cov-report=term-missing

lint:
	$(PYTHON) -m flake8 bot/ main.py --max-line-length=100
	$(PYTHON) -m mypy bot/ main.py --ignore-missing-imports
	$(PYTHON) -m black --check bot/ main.py
	$(PYTHON) -m isort --check-only bot/ main.py

format:
	$(PYTHON) -m black bot/ main.py tests/
	$(PYTHON) -m isort bot/ main.py tests/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
	rm -rf $(VENV)
