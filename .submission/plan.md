# Implementation Plan: `erk runs` Command

## Overview
Create `erk runs` command to view GitHub Actions status for plan implementations across all repository branches, showing the most recent run per branch with status & conclusion.

## Architecture: Following Fake-Driven Testing

This implementation follows the **8-step checklist for adding an integration class method** (from fake-driven-testing skill):

### Step 1-5: Integration Layer (`src/erk/core/github/`)

**1. Add `@abstractmethod` to ABC** (`abc.py`):
```python
@abstractmethod
def list_workflow_runs(
    self,
    repo_root: Path,
    workflow: str,
    limit: int = 50
) -> list[WorkflowRun]:
    """List workflow runs for a specific workflow."""
```

**2. Implement in RealGitHub** (`real.py`):
- Call `gh run list --workflow {workflow} --json --limit {limit}` via `run_subprocess_with_context()`
- Parse JSON response: `[{"databaseId": "123", "status": "completed", "conclusion": "success", "headBranch": "feat-1", "headSha": "abc123"}, ...]`
- Map to `WorkflowRun` dataclasses
- Use subprocess wrapper for rich error handling

**3. Implement in FakeGitHub** (`tests/fakes/github.py`):
- Return fixture data (list of `WorkflowRun` objects)
- Store in `_workflow_runs: list[WorkflowRun]` for test configuration
- No actual subprocess calls (in-memory only)

**4. Add mutation tracking** (N/A - this is a read operation):
- No mutation tracking needed (list operation is read-only)

**5. Implement in NoopGitHub** (`noop.py`):
- Delegate to wrapped implementation: `return self._github.list_workflow_runs(...)`
- Read operations always delegate

### Data Model (`src/erk/core/github/models.py` - new file)

Create `WorkflowRun` dataclass:
```python
@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    status: str          # "in_progress", "completed", "queued"
    conclusion: str | None  # "success", "failure", "cancelled" (None if in progress)
    branch: str
    head_sha: str
```

### Step 6-7: Test Integration Layer

**6. Unit test of fake** (`tests/unit/fakes/test_fake_github.py`):
- Test that `FakeGitHub.list_workflow_runs()` returns configured runs
- Test filtering by workflow name
- Test limit parameter
- Layer 1: Verify test infrastructure works

**7. Integration test of real** (`tests/integration/test_real_github.py`):
- Mock `subprocess.run()` with sample JSON response
- Verify `RealGitHub.list_workflow_runs()` constructs correct command
- Verify JSON parsing into `WorkflowRun` objects
- Layer 2: Validate real implementation with mocked subprocess

### Step 8-9: CLI Command and Business Logic

**8. Create CLI command** (`src/erk/cli/commands/runs.py`):

**Business logic:**
- Query runs: `runs = ctx.github.list_workflow_runs(repo.root, "implement-plan.yml")`
- Group by branch: `branch_to_latest: dict[str, WorkflowRun]` (keep most recent per branch)
- Format output with color coding:
  - `✓` (green) for success
  - `✗` (red) for failure
  - `⏳` (yellow) for in_progress
  - `⭕` (gray) for cancelled

**Output format:**
```
Plan Implementation Runs:

  feat-123  ✓ success       (run: 1234567890)
  feat-456  ✗ failure       (run: 1234567891)
  feat-789  ⏳ in_progress  (run: 1234567892)

View details: gh run view {run_id} --web
```

**9. Write business logic tests** (`tests/commands/test_runs.py`):
- **Layer 4**: Test over `FakeGitHub` (majority of tests)
- Test grouping (multiple runs → show latest per branch)
- Test status/conclusion formatting
- Test empty state (no runs)
- Test filtering to "implement-plan.yml" workflow
- Use `CliRunner` (NOT subprocess) for CLI testing

### CLI Registration

Update `src/erk/cli/__init__.py` to register `runs` command

## Testing Distribution (Fake-Driven Pattern)

| Layer | Test Type | Location | Coverage |
|-------|-----------|----------|----------|
| Layer 1 | Fake infrastructure | `tests/unit/fakes/test_fake_github.py` | ~5% |
| Layer 2 | Real integration (mocked) | `tests/integration/test_real_github.py` | ~10% |
| Layer 4 | Business logic over fakes | `tests/commands/test_runs.py` | ~70% |

**Total: ~85% of tests** (no Layer 3 pure unit tests needed - no pure utilities, no Layer 5 e2e needed - read operation)

## Design Decisions

✅ **Follow ABC/Real/Fake/Noop pattern** - Consistent with existing `GitHub` integration layer
✅ **Read operation delegates in NoopGitHub** - No dry-run behavior needed for queries
✅ **Test over fakes (Layer 4)** - Fast, in-memory, majority of test coverage
✅ **Use CliRunner** - NOT subprocess for CLI tests (faster, more reliable)
✅ **Minimal initial output** - Status/conclusion only (extensible for timing/commit info later)

## Extension Points (Future Work)

- `--branch` flag to filter specific branch
- `--limit N` flag for multiple runs per branch
- `--verbose` for timing, commit message, duration
- `--watch {run_id}` to delegate to `gh run watch`

## Implementation Checklist

- [ ] Create `WorkflowRun` dataclass in `src/erk/core/github/models.py`
- [ ] Add `list_workflow_runs()` abstract method to `GitHub` ABC
- [ ] Implement `list_workflow_runs()` in `RealGitHub`
- [ ] Implement `list_workflow_runs()` in `FakeGitHub`
- [ ] Implement `list_workflow_runs()` in `NoopGitHub`
- [ ] Write fake infrastructure tests (Layer 1)
- [ ] Write real integration tests (Layer 2)
- [ ] Create `runs.py` CLI command
- [ ] Write CLI command tests over fakes (Layer 4)
- [ ] Register command in `src/erk/cli/__init__.py`
- [ ] Run type checking with pyright
- [ ] Run formatting with ruff
- [ ] Run all tests
