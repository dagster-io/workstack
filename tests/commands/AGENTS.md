# CLI Command Testing Patterns

## Overview

All CLI command tests use dependency injection via WorkstackContext with fake implementations. Tests use Click's `CliRunner` to simulate command execution without actual filesystem or git operations.

## Subdirectory Organization

| Directory     | Focus                    | When to Load                           |
| ------------- | ------------------------ | -------------------------------------- |
| `workspace/`  | create, rename, rm, move | Workspace manipulation commands        |
| `navigation/` | switch, up, down         | Branch navigation commands             |
| `display/`    | status, tree, list       | Information display commands           |
| `shell/`      | Shell integration        | Shell wrapper generation and utilities |
| `management/` | plan                     | Workspace planning commands            |
| `setup/`      | init, config, completion | Initial configuration commands         |

## Standard Test Pattern

```python
from click.testing import CliRunner
from workstack.commands.create import create
from workstack.context import WorkstackContext
from tests.fakes.fake_gitops import FakeGitOps

def test_command_behavior() -> None:
    # Arrange: Set up fakes with desired state
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    ctx = WorkstackContext(
        git_ops=git_ops,
        # ... other dependencies
    )

    runner = CliRunner()

    # Act: Execute command
    result = runner.invoke(
        create,
        ["new-branch"],
        obj=ctx
    )

    # Assert: Verify behavior
    assert result.exit_code == 0
    assert "Created workspace" in result.output
    assert "new-branch" in git_ops.created_branches
```

## Common Assertions

### Exit Codes

```python
# Success
assert result.exit_code == 0

# User error (validation, missing args)
assert result.exit_code == 2

# Runtime error (git failure, filesystem issue)
assert result.exit_code == 1
```

### Output Verification

```python
# Check for expected messages
assert "Success message" in result.output
assert "Expected value" in result.output

# Check error messages
assert result.exit_code != 0
assert "Error: Expected error" in result.output
```

### State Changes

```python
# Verify mutations via fake's read-only properties
assert "branch-name" in git_ops.created_branches
assert "old-name" in git_ops.deleted_branches
assert git_ops.rename_history == [("old", "new")]
```

## Testing CLI Options

### Boolean Flags

```python
result = runner.invoke(command, ["--force", "arg"])
```

### Options with Values

```python
result = runner.invoke(command, ["--option", "value", "arg"])
```

### Multiple Arguments

```python
result = runner.invoke(command, ["arg1", "arg2"])
```

## Error Handling Tests

```python
def test_command_with_invalid_input() -> None:
    # Arrange: Set up state that will cause validation error
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "existing-branch"]
    )

    ctx = WorkstackContext(git_ops=git_ops)
    runner = CliRunner()

    # Act: Try to create duplicate branch
    result = runner.invoke(create, ["existing-branch"], obj=ctx)

    # Assert: Verify error handling
    assert result.exit_code != 0
    assert "already exists" in result.output
```

## Subprocess Interaction

Commands that use `subprocess.run` should inject `FakeShellOps`:

```python
from tests.fakes.fake_shell_ops import FakeShellOps

shell_ops = FakeShellOps()
shell_ops.add_command_result(
    "git status",
    returncode=0,
    stdout="clean working tree"
)

ctx = WorkstackContext(shell_ops=shell_ops)
```

## See Also

- [../../docs/TESTING.md#unit-test-pattern](../../docs/TESTING.md#unit-test-pattern)
- [../CLAUDE.md](../CLAUDE.md) - Overview of test structure
- [../fakes/](../fakes/) - Available fake implementations
