# Test Organization

This package uses a layered testing architecture to separate fast unit tests from slow integration tests, following erk's testing patterns.

## Directory Structure

- **`unit/`** - Fast unit tests (~2s for 578 tests)
  - In-memory, no filesystem I/O
  - All dependencies injected via fakes
  - Tests business logic in isolation

- **`integration/`** - Slow integration tests (~14s for 2 tests)
  - Real subprocess calls, actual filesystem operations
  - Tests CLI interactions and edge cases requiring actual tools
  - Isolated from fast unit tests to enable rapid development feedback

- **`fakes/`** - Fake implementations shared across all test layers
  - FakeArtifactRepository, FakeClaudeCliOps, etc.
  - Reused by unit tests for dependency injection

## Running Tests

```bash
# Fast unit tests only (development)
pytest packages/dot-agent-kit/tests/unit/

# Slow integration tests
pytest packages/dot-agent-kit/tests/integration/

# All tests
pytest packages/dot-agent-kit/tests/
```

## Philosophy

This organization enables:

1. **Rapid feedback loop** - `pytest tests/unit/` completes in ~2s for quick iterations
2. **Clear separation** - Integration tests don't block fast unit tests
3. **Dependency injection** - All tests use fakes, no mock.patch or hardcoded paths
4. **Consistent with erk** - Matches erk's 4-layer testing architecture (fakes → mocked real → business logic → E2E)

See [AGENTS.md](../AGENTS.md) in the parent directory for more information about coding standards.
