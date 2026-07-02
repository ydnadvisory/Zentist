.PHONY: dev lint format test audit build

dev:
	uv sync --all-groups

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check src

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

audit:
	uv run pip-audit

build:
	uv build
