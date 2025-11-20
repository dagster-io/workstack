# Workspace Manipulation Command Patterns

## Overview

This directory contains tests for commands that create, rename, remove, and move workspaces. These commands manipulate both the git branch structure and filesystem state.

## Commands in This Directory

- `test_add.py` - Tests for `erk add` command
- `test_rename.py` - Tests for `erk rename` command
- `test_remove.py` - Tests for `erk remove` command
- `test_move.py` - Tests for `erk move` command

## Common Test Setup

All workspace manipulation tests follow this pattern:

```python
from click.testing import CliRunner
from erk.commands.create import create
from erk.context import ErkContext
from tests.fakes.fake_git import FakeGit
from tests.fakes.fake_graphite import FakeGraphite

def test_workspace_operation() -> None:
    # Arrange: Set up git state
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "existing-branch"],
        remote_tracking={"main": "origin/main"}
    )

    graphite = FakeGraphite()

    ctx = ErkContext(
        git=git,
        graphite=graphite,
        cwd="/fake/workspace"
    )

    runner = CliRunner()

    # Act: Execute command
    result = runner.invoke(create, ["new-branch"], obj=ctx)

    # Assert: Verify behavior
    assert result.exit_code == 0
```

## Filesystem State Assertions

### Directory Creation/Removal

```python
# Verify directory was created
result = runner.invoke(create, ["new-workspace"], obj=ctx)
assert result.exit_code == 0
# In real tests, check actual filesystem via CliRunner.isolated_filesystem()
```

### Working Directory Changes

```python
# Commands that change directories should be verified via shell wrappers
assert "cd /path/to/workspace" in shell.executed_commands
```

## Git State Verification

### Branch Creation

```python
result = runner.invoke(create, ["new-branch"], obj=ctx)
assert result.exit_code == 0
assert "new-branch" in git.created_branches
```

### Branch Deletion

```python
result = runner.invoke(delete, ["old-branch"], obj=ctx)
assert result.exit_code == 0
assert "old-branch" in git.deleted_branches
```

### Branch Renaming

```python
result = runner.invoke(rename, ["old-name", "new-name"], obj=ctx)
assert result.exit_code == 0
assert git.rename_history == [("old-name", "new-name")]
```

### Branch Existence Checks

```python
# Test trying to create duplicate branch
git = FakeGit(
    current_branch="main",
    all_branches=["main", "existing"]
)

result = runner.invoke(create, ["existing"], obj=ctx)
assert result.exit_code != 0
assert "already exists" in result.output
```

## Testing Options and Flags

### Force Flag

```python
# Test --force flag for destructive operations
result = runner.invoke(delete, ["--force", "branch-name"], obj=ctx)
assert result.exit_code == 0
```

### Dry Run Mode

```python
# Test --dry-run doesn't actually mutate
result = runner.invoke(delete, ["--dry-run", "branch"], obj=ctx)
assert result.exit_code == 0
assert "branch" not in git.deleted_branches
assert "Would delete" in result.output
```

## Graphite Stack Integration

Commands may need to interact with Graphite stacks:

```python
graphite = FakeGraphite()
graphite.add_stack("feature/parent", ["feature/child1", "feature/child2"])

ctx = ErkContext(
    git=git,
    graphite=graphite
)

# Test command that affects stacks
result = runner.invoke(rename, ["feature/parent", "feature/new-parent"], obj=ctx)
assert result.exit_code == 0
assert graphite.renamed_stacks == [("feature/parent", "feature/new-parent")]
```

## Error Scenarios to Test

1. **Branch doesn't exist**: Attempting to rename/remove non-existent branch
2. **Branch already exists**: Creating/renaming to existing branch name
3. **Currently checked out**: Attempting to delete current branch
4. **Invalid names**: Branch names with invalid characters
5. **Permission issues**: Filesystem permission errors
6. **Git conflicts**: Branch has uncommitted changes

## Common Patterns

### Testing Multi-Step Operations

```python
# Commands that do multiple operations should verify each step
result = runner.invoke(move, ["branch-name", "/new/location"], obj=ctx)
assert result.exit_code == 0

# Verify git operations
assert "branch-name" in git.checked_out_branches

# Verify filesystem operations
assert shell.executed_commands[-1].startswith("cd /new/location")
```

### Testing Output Messages

```python
result = runner.invoke(create, ["new-workspace"], obj=ctx)
assert result.exit_code == 0
assert "Created workspace" in result.output
assert "new-workspace" in result.output
assert "Successfully" in result.output or "✓" in result.output
```

## See Also

- [../CLAUDE.md](../CLAUDE.md) - General CLI command patterns
- [../../docs/TESTING.md](../../../docs/TESTING.md) - Complete testing guide
- [../../fakes/git.py](../../fakes/git.py) - FakeGit implementation
