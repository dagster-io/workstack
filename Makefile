.PHONY: format format-check lint prettier prettier-check pyright upgrade-pyright test all-ci check clean publish fix

prettier:
	prettier --write '**/*.md' --ignore-path .gitignore

prettier-check:
	prettier --check '**/*.md' --ignore-path .gitignore

format:
	uv run ruff format

format-check:
	uv run ruff format --check

lint:
	uv run ruff check

fix:
	uv run ruff check --fix --unsafe-fixes

pyright:
	uv run pyright

upgrade-pyright:
	uv remove pyright --group dev && uv add --dev pyright

test-workstack-dev:
	cd packages/workstack-dev && uv run pytest

test-dot-agent-kit:
	cd packages/dot-agent-kit && uv run pytest

test: test-workstack-dev test-dot-agent-kit

check:
	uv run dot-agent check

all-ci: lint format-check prettier-check pyright test check

# Clean build artifacts
clean:
	rm -rf dist/*.whl dist/*.tar.gz

# Build workstack and dot-agent-kit packages
build: clean
	uv build --package dot-agent-kit -o dist
	uv build --package workstack -o dist
	uv build --package dev-runners-da-kit -o dist

# Publish packages to PyPI
# Use workstack-dev publish-to-pypi command instead (recommended)
publish: build
	@echo "Publishing dot-agent-kit..."
	uvx uv-publish ./dist/dot_agent_kit-*.whl ./dist/dot_agent_kit-*.tar.gz
	@echo "Publishing workstack..."
	uvx uv-publish ./dist/workstack-*.whl ./dist/workstack-*.tar.gz
	@echo "✓ Packages published successfully"
