# Display Command Testing Patterns

## Overview

This directory contains tests for commands that display information about workspaces, branches, and stacks. These commands format and present data without modifying state.

## Commands in This Directory

- `test_status.py` - Tests for `erk status` command
- `list/` - Tests for `erk list` command and variants

## Common Test Setup

Display commands typically read state but don't modify it:

```python
from click.testing import CliRunner
from erk.commands.status import status
from erk.context import ErkContext
from tests.fakes.fake_gitops import FakeGitOps
from tests.fakes.fake_github_ops import FakeGitHubOps

def test_display_command() -> None:
    # Arrange: Set up state to display
    git_ops = FakeGitOps(
        current_branch="feature/test",
        all_branches=["main", "feature/test", "feature/other"]
    )

    github_ops = FakeGitHubOps()
    github_ops.add_pr("feature/test", number=123, state="open")

    ctx = ErkContext(
        git_ops=git_ops,
        github_ops=github_ops
    )

    runner = CliRunner()

    # Act: Execute command
    result = runner.invoke(status, [], obj=ctx)

    # Assert: Verify output formatting
    assert result.exit_code == 0
    assert "feature/test" in result.output
    assert "#123" in result.output
```

## Output Formatting Assertions

### Table Rendering

```python
# Verify table headers present
result = runner.invoke(list_cmd, [], obj=ctx)
assert result.exit_code == 0
assert "Branch" in result.output
assert "PR" in result.output
assert "Status" in result.output

# Verify table rows
assert "feature/test" in result.output
```

### Tree Structure Display

```python
# Verify hierarchical display
result = runner.invoke(tree, [], obj=ctx)
assert result.exit_code == 0

# Check for tree characters (├── └── │)
assert "├──" in result.output or "└──" in result.output
assert "main" in result.output
```

### Colored Output

Display commands use colors for visual emphasis:

```python
# Output may contain ANSI color codes
# Use click.unstyle() to strip colors for testing
from click import unstyle

result = runner.invoke(status, [], obj=ctx)
clean_output = unstyle(result.output)

assert "Open" in clean_output  # Status without color codes
```

## GitHub Data Integration

Many display commands show PR information:

```python
github_ops = FakeGitHubOps()

# Add PR data
github_ops.add_pr(
    "feature/branch",
    number=456,
    state="open",
    title="Add new feature",
    url="https://github.com/org/repo/pull/456"
)

ctx = ErkContext(
    git_ops=git_ops,
    github_ops=github_ops
)

result = runner.invoke(status, [], obj=ctx)
assert "#456" in result.output
assert "Add new feature" in result.output
```

## Testing Different Display Modes

### Verbose Mode

```python
# Test --verbose flag shows additional details
result = runner.invoke(list_cmd, ["--verbose"], obj=ctx)
assert result.exit_code == 0
# Verify additional columns/info present
```

### Compact Mode

```python
# Test compact output
result = runner.invoke(status, ["--compact"], obj=ctx)
assert result.exit_code == 0
# Verify shorter format
```

## Empty State Handling

```python
# Test display when no data available
git_ops = FakeGitOps(
    current_branch="main",
    all_branches=["main"]  # Only main branch
)

result = runner.invoke(list_cmd, [], obj=ctx)
assert result.exit_code == 0
assert "No workspaces" in result.output or "None found" in result.output
```

## Error Display

```python
# Test error message formatting
github_ops = FakeGitHubOps()
github_ops.set_error("API rate limit exceeded")

result = runner.invoke(status, [], obj=ctx)
# Command should handle gracefully
assert "rate limit" in result.output.lower()
```

## Filtering and Sorting

### Branch Filtering

```python
# Test filtering by pattern
result = runner.invoke(list_cmd, ["--filter", "feature/*"], obj=ctx)
assert "feature/test" in result.output
assert "main" not in result.output  # Filtered out
```

### Sort Order

```python
# Test sort options
result = runner.invoke(list_cmd, ["--sort", "name"], obj=ctx)
# Verify branches appear in alphabetical order
```

## Performance Considerations

Display commands should be fast and not modify state:

```python
def test_display_no_side_effects() -> None:
    git_ops = FakeGitOps(current_branch="main", all_branches=["main"])

    ctx = ErkContext(git_ops=git_ops)
    runner = CliRunner()

    result = runner.invoke(status, [], obj=ctx)

    # Verify no mutations occurred
    assert len(git_ops.created_branches) == 0
    assert len(git_ops.deleted_branches) == 0
```

## Testing Output Consistency

```python
# Multiple invocations should produce same output
result1 = runner.invoke(status, [], obj=ctx)
result2 = runner.invoke(status, [], obj=ctx)

assert result1.output == result2.output
```

## See Also

- [../CLAUDE.md](../CLAUDE.md) - General CLI command patterns
- [list/CLAUDE.md](list/CLAUDE.md) - List command specific patterns
- [../../docs/TESTING.md](../../../docs/TESTING.md) - Complete testing guide
