# Shared per-package workflow, included by every package Makefile so the commands AGENTS.md
# prescribes have one definition instead of one copy per package. Six copies had already
# drifted into two variants differing only by stray indentation.

PACKAGE := $(notdir $(CURDIR))
WORKSPACE := $(CURDIR)/../..

.PHONY: dev check test clean

dev:
	uv sync --group dev

# Type checking runs from the workspace root on purpose. Invoked from inside a package,
# Pyright treats that package as the project root and resolves the workspace config's
# relative settings — stubPath, extraPaths — against it, losing them without a diagnostic.
check:
	uv run ruff check .
	uv run ruff format --check .
	cd $(WORKSPACE) && uv run pyright packages/$(PACKAGE)/src packages/$(PACKAGE)/tests

# Exit status 5 means "no tests collected", which is not a failure for a package without any.
test:
	uv run pytest -v || [ $$? -eq 5 ]

clean:
	rm -rf .coverage dist htmlcov .pytest_cache .ruff_cache
