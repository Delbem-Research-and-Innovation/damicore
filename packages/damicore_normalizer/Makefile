.PHONY: dev check test clean

dev:
	uv sync --group dev

check:
	 uv run ruff check .
	uv run ruff format --check .
	uv run pyright src tests

test:
	uv run pytest -v || [ $$? -eq 5 ]

clean:
	rm -rf .coverage dist htmlcov .pytest_cache .ruff_cache
