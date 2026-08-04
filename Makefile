.PHONY: help install check test build clean

PUBLIC_PACKAGES := damicore_normalizer damicore_distance damicore_tree_builder damicore_clusterizer damicore

help:
	@echo "Workspace commands:"
	@echo "  install  Install all workspace dependencies and git hooks"
	@echo "  check    Lint and type-check the workspace"
	@echo "  test     Run all tests with coverage gates"
	@echo "  build    Build the five public distributions"
	@echo "  clean    Remove build artifacts and the shared .venv"

install:
	uv sync --all-packages --group dev
	pre-commit install

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright

test:
	uv run pytest --cov --cov-report=term-missing

build:
	@set -e; for package in $(PUBLIC_PACKAGES); do uv build --package $$package; done

clean:
	@echo "Remove .venv, dist, coverage, and test caches explicitly when needed."
