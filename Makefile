.PHONY: help install check test clean

export PYRIGHT_PYTHON_FORCE_VERSION := latest

PACKAGES := $(patsubst %/Makefile,%,$(wildcard packages/*/Makefile))

help:
	@echo "Workspace commands:"
	@echo "  install  Install all workspace dependencies and git hooks"
	@echo "  check    Lint + type-check all packages"
	@echo "  test     Run all package tests"
	@echo "  clean    Remove build artifacts and the shared .venv"

install:
	uv sync --all-packages --group dev
	pre-commit install

check:
	@set -e; for d in $(PACKAGES); do echo ">>> $$d"; $(MAKE) -C $$d check; done

test:
	@set -e; for d in $(PACKAGES); do echo ">>> $$d"; $(MAKE) -C $$d test; done

clean:
	@set -e; for d in $(PACKAGES); do $(MAKE) -C $$d clean; done
	rm -rf .venv
