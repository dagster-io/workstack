<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# Plan: Add `Ensure.system_exit_boundary` Context Manager

## Summary

Create a reusable CLI error boundary context manager and apply it across all kit CLI commands that catch `RuntimeError` and re-raise as `SystemExit(1)`.

## New File

**`packages/erk-shared/src/erk_shared/cli.py`**

```python
"""CLI error boundary utilities for kit CLI commands."""

from collections.abc import Iterator
from contextlib import contextmanager

import click


class Ensure:
    """Namespace for CLI error boundary utilities."""

    @staticmethod
    @contextmanager
    def system_exit_boundary(message: str) -> Iterator[None]:
        """Catch RuntimeError and re-raise as SystemExit(1) with error message.

        Usage:
            with Ensure.system_exit_boundary("Failed to create issue"):
                github.create_issue(repo_root, title, body, labels)
        """
        try:
            yield
        except RuntimeError as e:
            click.echo(f"Error: {message}: {e}", err=True)
            raise SystemExit(1) from e
```

## Files to Refactor

All 8 files with `except RuntimeError as e:` pattern in kit CLI commands:

1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_plan_from_context.py`
2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_enriched_plan_from_context.py`
3. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_erp_from_issue.py`
4. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_issue.py`
5. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_start_comment.py`
6. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/comment_worktree_creation.py`
7. `src/erk/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py`
8. `src/erk/data/kits/erk/kit_cli_commands/erk/post_completion_comment.py`

## Transformation Pattern

**Before:**
```python
try:
    github.ensure_label_exists(...)
except RuntimeError as e:
    click.echo(f"Error: Failed to ensure label exists: {e}", err=True)
    raise SystemExit(1) from e
```

**After:**
```python
from erk_shared.cli import Ensure

with Ensure.system_exit_boundary("Failed to ensure label exists"):
    github.ensure_label_exists(...)
```

## Execution Steps

1. Create `erk_shared/cli.py` with `Ensure` class
2. Update `erk_shared/__init__.py` docstring to document new module
3. Refactor each of the 8 files to use `Ensure.system_exit_boundary`
4. Run pyright and tests

## Context & Understanding

### Architectural Insights

1. **Consistent Error Boundary Pattern**: All 8 commands follow the same error handling pattern for `RuntimeError` exceptions, indicating a systematic refactoring opportunity across the CLI command suite.

2. **Namespace Design Choice**: Using a static class `Ensure` as a namespace (rather than module-level functions or a single function) maintains consistency with other utility patterns in the codebase and provides clear semantic intent through the class name.

3. **Context Manager Justification**: Using `@contextmanager` decorator reduces boilerplate compared to custom `__enter__`/`__exit__` implementations while maintaining readability and testability. The context manager pattern allows for minimal indentation changes in refactored code.

4. **Shared Package Location**: Placing this utility in `erk_shared` rather than `dot-agent-kit` or `erk` directly ensures it's accessible to all CLI commands regardless of which package they're defined in (both dot-agent-kit and erk packages need this functionality).

### Domain Logic & Business Rules

1. **Click Integration Pattern**: The utility integrates with Click's `click.echo()` and stderr redirection, which is the standard in all CLI commands. Error output must always use `err=True` to ensure error messages go to stderr, not stdout (important for command output parsing).

2. **Exit Code Convention**: The convention to use `SystemExit(1)` for all runtime errors is consistent across all commands and matches standard Unix conventions. This allows calling code to distinguish between success (0) and failure (1).

3. **Error Message Format**: All commands follow the pattern `f"Error: {message}: {e}"` which provides both a high-level message (describing what failed) and the underlying exception details. This format is preserved in the context manager to ensure consistency.

4. **Exception Chaining**: Using `raise SystemExit(1) from e` maintains the exception chain for debugging while transforming the exception type for CLI exit codes. This is important for stack trace preservation.

### Known Pitfalls

1. **Mixed Error Handling Patterns**: Not all commands in the target list use identical error handling. For example, `post_progress_comment.py` and `post_completion_comment.py` use different error handling (they return JSON errors instead of stderr messages and use `SystemExit(0)` instead of `SystemExit(1)` in some paths). The refactoring should only apply to commands using the standard RuntimeError -> SystemExit(1) pattern, not to commands with special error handling requirements.

2. **Context Manager Nesting**: Some commands wrap multiple operations. Ensure that nested context managers don't mask earlier exceptions (they won't - the first exception to occur will propagate). Test the refactored code to verify error handling behavior is preserved.

### Raw Discoveries Log

1. **Exact File Count**: Located exactly 8 files with the RuntimeError pattern:
   - 6 files in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/`
   - 2 files in `src/erk/data/kits/erk/kit_cli_commands/erk/`

2. **File-by-File Error Patterns**:
   - `create_plan_from_context.py`: 3 try-except blocks (label, create, update)
   - `create_enriched_plan_from_context.py`: 2 try-except blocks (label, create)
   - `create_erp_from_issue.py`: 1 try-except block (plan fetch)
   - `create_issue.py`: 1 try-except block (create issue)
   - `post_start_comment.py`: 1 try-except block (add comment)
   - `comment_worktree_creation.py`: 1 try-except block (add comment)
   - `post_progress_comment.py`: 1 try-except block (add comment)
   - `post_completion_comment.py`: 1 try-except block (add comment)
   - **Total: 11 try-except blocks across 8 files**

### Implementation Risks

1. **Selective Application Required**: This refactoring should ONLY apply to the 8 files using the standard RuntimeError -> SystemExit(1) pattern. Commands with different error handling (like graceful JSON errors with SystemExit(0)) should NOT be refactored with this utility, as it would change their semantics.

2. **Testing Scope**: All 8 commands should have tests that verify:
   - Normal success paths still work (no regression)
   - RuntimeError exceptions are properly caught and converted to SystemExit(1)
   - Error messages are properly formatted and go to stderr
   - The exception chain is preserved (using `from e`)

3. **Documentation Update**: The __init__.py docstring needs to be updated to include the new `cli` module, listing the `Ensure` class and its `system_exit_boundary` context manager.

</details>
<!-- /erk:metadata-block:plan-body -->

---

## Execution Commands

**Submit to Erk Queue:**
```bash
erk submit 1141
```

---

### Local Execution

**Standard mode (interactive):**
```bash
erk implement 1141
```

**Yolo mode (fully automated, skips confirmation):**
```bash
erk implement 1141 --yolo
```

**Dangerous mode (auto-submit PR after implementation):**
```bash
erk implement 1141 --dangerous
```