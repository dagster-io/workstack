.PHONY: format format-check lint prettier prettier-check pyright upgrade-pyright test all-ci check md-check clean publish fix sync-dignified-python-universal

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

# === Package-specific test targets ===

test-workstack-dev:
	cd packages/workstack-dev && uv run pytest -n auto

test-dot-agent-kit:
	cd packages/dot-agent-kit && uv run pytest -n auto

# === Workstack test targets ===

# Unit tests: Fast, in-memory tests using fakes (tests/unit/, tests/commands/, tests/core/)
# These provide quick feedback for development iteration
test-unit-workstack:
	uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto

# Integration tests: Slower tests with real I/O and subprocess calls (tests/integration/)
# These verify that abstraction layers correctly wrap external tools
test-integration-workstack:
	uv run pytest tests/integration/ -n auto

# All workstack tests (unit + integration)
test-all-workstack: test-unit-workstack test-integration-workstack

# Backward compatibility: test-workstack now runs unit tests only
test-workstack: test-unit-workstack

# === Combined test targets ===

# Default 'make test': Run unit tests only (fast feedback loop for development)
# Includes: workstack unit tests + all workstack-dev tests + all dot-agent-kit tests
test: test-unit-workstack test-workstack-dev test-dot-agent-kit

# Integration tests: Run only integration tests across all packages
test-integration: test-integration-workstack

# All tests: Run both unit and integration tests (comprehensive validation)
test-all: test-all-workstack test-workstack-dev test-dot-agent-kit

check:
	uv run dot-agent check

md-check:
	uv run dot-agent md check

# Removed: land-branch command has been deprecated

# Sync universal Python standards to all Dignified Python kits
sync-dignified-python-universal:
	@echo "Syncing universal Python standards..."
	cp packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python-shared/universal-python-standards.md \
	   packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python-310/skills/dignified-python/UNIVERSAL.md
	cp packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python-shared/universal-python-standards.md \
	   packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python-313/skills/dignified-python/UNIVERSAL.md
	@echo "✓ Universal standards synced to both kits"

# CI target: Run all tests (unit + integration) for comprehensive validation
all-ci: lint format-check prettier-check md-check pyright test-all check

# Clean build artifacts
clean:
	rm -rf dist/*.whl dist/*.tar.gz

# Build workstack and dot-agent-kit packages
build: clean
	uv build --package dot-agent-kit -o dist
	uv build --package workstack -o dist

# Publish packages to PyPI
# Use workstack-dev publish-to-pypi command instead (recommended)
publish: build
	workstack-dev publish-to-pypi
