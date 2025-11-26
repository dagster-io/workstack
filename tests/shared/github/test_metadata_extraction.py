"""Unit tests for metadata extraction functions.

Layer 3 (Pure Unit Tests): Tests for metadata extraction logic with zero dependencies.
Tests extraction functions that parse metadata blocks from issue bodies.
"""

from erk_shared.github.metadata import (
    extract_plan_header_dispatch_info,
    extract_plan_header_worktree_name,
)


def test_extract_plan_header_worktree_name_found() -> None:
    """Extract worktree_name from plan-header block when present."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: optimize-feature-b-24-01-15
last_dispatched_run_id: null
last_dispatched_at: null
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_worktree_name(issue_body)
    assert result == "optimize-feature-b-24-01-15"


def test_extract_plan_header_worktree_name_missing_block() -> None:
    """Return None when plan-header block is missing."""
    issue_body = """This is a plain issue body without any metadata blocks."""

    result = extract_plan_header_worktree_name(issue_body)
    assert result is None


def test_extract_plan_header_worktree_name_missing_field() -> None:
    """Return None when worktree_name field is missing from block."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    result = extract_plan_header_worktree_name(issue_body)
    assert result is None


def test_extract_plan_header_worktree_name_with_dispatch_info() -> None:
    """Extract worktree_name from block that also has dispatch info."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch-b-24-01-15
last_dispatched_run_id: '1234567890'
last_dispatched_at: '2024-01-15T11:00:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->"""

    worktree = extract_plan_header_worktree_name(issue_body)
    run_id, dispatched_at = extract_plan_header_dispatch_info(issue_body)

    assert worktree == "feature-branch-b-24-01-15"
    assert run_id == "1234567890"
    assert dispatched_at == "2024-01-15T11:00:00Z"
