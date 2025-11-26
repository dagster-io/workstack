# Refactor plan check_cmd.py to Extract Reusable Helpers

## Rationale

- Minimal disruption to existing code structure
- Follows proven pattern (navigation_helpers.py)
- Functions accept ErkContext for dependency injection
- Easy to test independently of Click framework
- Can be promoted to service layer later if requirements grow

## Current State Analysis

check_cmd.py (138 lines) contains:
- Identifier parsing logic (lines 18-41): Converts string/URL to issue number
- GitHub API interaction (lines 76-79, 101-105): Fetches issue and comments via ctx.issues
- Validation logic (lines 83-118): Four schema checks with pass/fail tracking
- Output formatting (lines 68-69, 121-136): User-facing messages with click.style() colors
- Error handling: SystemExit for invalid identifiers, API failures, validation failures

Duplication identified:
- check_cmd.py lines 18-41 and retry_cmd.py lines 40-61 both implement URL parsing with nearly identical logic

## Proposed Structure

### 1. Create src/erk/cli/commands/plan/shared.py

Purpose: Eliminate duplication between check_cmd.py and retry_cmd.py

```python
def parse_plan_identifier(identifier: str) -> int:
    """Parse issue number from numeric string or GitHub URL.

    Args:
        identifier: Issue number string (e.g., "42") or GitHub URL

    Returns:
        Issue number as integer

    Raises:
        ValueError: If identifier format is invalid
    """
    # Move logic from check_cmd.py _parse_identifier()
```

### 2. Create src/erk/cli/commands/plan/check_helpers.py

Purpose: Reusable validation logic testable without Click

```python
from erk_shared.github.metadata import MetadataBlock

def validate_plan_header_exists(issue_body: str) -> tuple[bool, str]:
    """Check if plan-header metadata block exists in issue body."""
    # Returns (True, "plan-header metadata block present") or (False, "...")

def validate_plan_header_schema(metadata_block: MetadataBlock) -> tuple[bool, str]:
    """Validate plan-header has required fields."""
    # Uses PlanHeaderSchema().validate(), returns pass/fail tuple

def validate_first_comment_exists(comments: list[str]) -> tuple[bool, str]:
    """Check if issue has at least one comment."""
    # Returns (True, "First comment exists") or (False, "...")

def validate_plan_body_extractable(comment_body: str) -> tuple[bool, str]:
    """Check if plan-body content can be extracted from comment."""
    # Uses extract_plan_from_comment(), returns pass/fail tuple
```

Design rationale:
- Each validation function returns (passed: bool, description: str) tuple
- Functions are pure - no side effects, no SystemExit
- Can be tested with direct calls, no CliRunner needed
- CLI layer handles output formatting and exit codes

### 3. Refactor src/erk/cli/commands/plan/check_cmd.py

New structure (~60 lines):

```python
from erk.cli.commands.plan.check_helpers import (
    validate_plan_header_exists,
    validate_plan_header_schema,
    validate_first_comment_exists,
    validate_plan_body_extractable,
)
from erk.cli.commands.plan.shared import parse_plan_identifier

@click.command("check")
@click.argument("identifier", type=str)
@click.pass_obj
def check_plan(ctx: ErkContext, identifier: str) -> None:
    """Validate plan's format against Schema v2."""
    # 1. Parse identifier via shared function
    # 2. Fetch issue/comments from GitHub
    # 3. Call validation helpers to build checks list
    # 4. Format and output results with click.style()
    # 5. Exit with appropriate code
```

Responsibilities after refactoring:
- CLI argument handling (Click decorator)
- Output formatting (colors, spacing)
- Error message display
- Exit code management
- GitHub API orchestration (fetch issue, then comments)

Removed from check_cmd.py:
- Validation logic → check_helpers.py
- URL parsing → shared.py

### 4. Update src/erk/cli/commands/plan/retry_cmd.py

Replace lines 40-61 (identifier parsing) with:

```python
from erk.cli.commands.plan.shared import parse_plan_identifier

# In retry_plan():
try:
    issue_number = parse_plan_identifier(identifier)
except ValueError as e:
    user_output(click.style("Error: ", fg="red") + str(e))
    raise SystemExit(1) from e
```

Benefits:
- Eliminates 22 lines of duplication
- Consistent error messages across commands
- Single source of truth for parsing logic

## Testing Strategy

### Unit Tests: tests/unit/commands/plan/test_check_helpers.py

Test each validation function independently:

```python
from erk.cli.commands.plan.check_helpers import validate_plan_header_exists

def test_validate_plan_header_exists_with_valid_block() -> None:
    issue_body = render_metadata_block(MetadataBlock("plan-header", {...}))
    passed, description = validate_plan_header_exists(issue_body)
    assert passed is True
    assert description == "plan-header metadata block present"

def test_validate_plan_header_exists_with_missing_block() -> None:
    issue_body = "No metadata here"
    passed, description = validate_plan_header_exists(issue_body)
    assert passed is False
    # ... test other validation functions similarly
```

Advantages:
- Fast execution (no CliRunner, no context setup)
- Clear failure messages (direct function calls)
- High coverage (test all branches easily)

### Unit Tests: tests/unit/commands/plan/test_shared.py

Test identifier parsing edge cases:

```python
from erk.cli.commands.plan.shared import parse_plan_identifier

def test_parse_identifier_with_number_string() -> None:
    assert parse_plan_identifier("42") == 42

def test_parse_identifier_with_github_url() -> None:
    assert parse_plan_identifier("https://github.com/owner/repo/issues/42") == 42

def test_parse_identifier_with_invalid_format() -> None:
    with pytest.raises(ValueError, match="Invalid identifier"):
        parse_plan_identifier("not-a-number")
```

### Integration Tests: tests/commands/plan/test_check.py (existing)

Keep existing tests unchanged - they verify end-to-end behavior:
- test_check_valid_plan_passes() - Full success path
- test_check_missing_plan_header_fails() - Missing block detection
- test_check_github_url_parsing() - URL handling
- (6 more tests covering various failure modes)

These tests remain the source of truth for CLI behavior.

## Implementation Plan

### Step 1: Create shared.py with identifier parsing

1. Create src/erk/cli/commands/plan/shared.py
2. Move _parse_identifier() logic from check_cmd.py, rename to parse_plan_identifier()
3. Add comprehensive docstring and type hints
4. Create tests/unit/commands/plan/test_shared.py with 5+ test cases
5. Run uv run pytest tests/unit/commands/plan/test_shared.py - verify all pass

### Step 2: Create check_helpers.py with validation logic

1. Create src/erk/cli/commands/plan/check_helpers.py
2. Extract four validation functions from check_cmd.py lines 83-118
3. Each function returns (bool, str) tuple for pass/fail and description
4. Create tests/unit/commands/plan/test_check_helpers.py with 12+ test cases
5. Run uv run pytest tests/unit/commands/plan/test_check_helpers.py - verify >90% coverage

### Step 3: Refactor check_cmd.py to use helpers

1. Update imports in check_cmd.py to include new helpers
2. Replace validation blocks (lines 83-118) with helper function calls
3. Replace _parse_identifier() with shared.parse_plan_identifier()
4. Simplify to ~60 lines focused on CLI concerns
5. Run uv run pytest tests/commands/plan/test_check.py - ALL existing tests must pass unchanged
6. Manually test erk plan check 42 - verify output identical to before

### Step 4: Update retry_cmd.py to use shared parser

1. Update imports in retry_cmd.py to include shared.parse_plan_identifier
2. Replace lines 40-61 with call to shared parser
3. Run uv run pytest tests/commands/plan/test_retry.py - verify no regressions
4. Manually test erk plan retry 42 - verify behavior unchanged

### Step 5: Verify complete system

1. Run full test suite: uv run pytest tests/commands/plan/
2. Run pyright: uv run pyright src/erk/cli/commands/plan/
3. Manual smoke test both commands with various identifiers
4. Verify no import cycles or missing dependencies

## Files Changed Summary

| File                  | Lines Before | Lines After | Change Type                       |
|-----------------------|--------------|-------------|-----------------------------------|
| check_cmd.py          | 138          | ~60         | Major refactor                    |
| retry_cmd.py          | 163          | ~140        | Minor update (remove duplication) |
| shared.py             | 0            | ~30         | New file                          |
| check_helpers.py      | 0            | ~80         | New file                          |
| test_shared.py        | 0            | ~50         | New file                          |
| test_check_helpers.py | 0            | ~150        | New file                          |

Total new test coverage: ~200 lines of unit tests for previously untestable logic

## Benefits

1. **Reusability**: Validation logic can be imported by webhooks, background jobs, or other commands
2. **Testability**: Unit tests for helpers are faster and more focused than integration tests
3. **Maintainability**: Clear separation between CLI (formatting, exit codes) and business logic (validation)
4. **DRY principle**: Eliminates identifier parsing duplication
5. **Type safety**: Helper functions can have strict type hints verified by pyright
6. **Future flexibility**: Easy to add new validation checks or modify existing ones

## Non-Goals

- ❌ Change CLI interface or output format
- ❌ Add new validation checks (scope is refactoring only)
- ❌ Create service classes (helpers are sufficient for current complexity)
- ❌ Modify existing test expectations (integration tests stay unchanged)