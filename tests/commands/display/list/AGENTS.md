# List Command Testing Patterns

## Overview

The `erk list` command is the most complex display command, supporting multiple modes (default, stacks, verbose) and showing PR information, stack hierarchies, and filtering options.

## Test Files in This Directory

- `test_basic.py` - Basic list functionality and formatting
- `test_pr_info.py` - PR information display integration
- `test_root_filtering.py` - Root branch filtering logic
- `test_stacks.py` - Stack hierarchy display
- `test_trunk_detection.py` - Main/trunk branch detection

## List Command Modes

### Default Mode

```python
from erk.commands.list import list as list_cmd

def test_list_default() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature/a", "feature/b"]
    )

    runner = CliRunner()
    result = runner.invoke(list_cmd, [], obj=ErkContext(git=git))

    assert result.exit_code == 0
    assert "feature/a" in result.output
    assert "feature/b" in result.output
```

### Stacks Mode

```python
def test_list_stacks() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "parent", "parent/child"]
    )

    graphite = FakeGraphite()
    graphite.add_stack("parent", ["parent/child"])

    ctx = ErkContext(git=git, graphite=graphite)
    runner = CliRunner()

    result = runner.invoke(list_cmd, ["--stacks"], obj=ctx)

    assert result.exit_code == 0
    # Verify hierarchical display
    assert "parent" in result.output
    assert "parent/child" in result.output
```

### Verbose Mode

```python
def test_list_verbose() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature/test"]
    )

    runner = CliRunner()
    result = runner.invoke(list_cmd, ["--verbose"], obj=ctx)

    assert result.exit_code == 0
    # Verify additional columns present
    assert "Last Commit" in result.output or "Updated" in result.output
```

## PR Information Display

The list command integrates with GitHub to show PR status:

```python
def test_list_with_pr_info() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature/test"]
    )

    github = FakeGitHub()
    github.add_pr(
        "feature/test",
        number=123,
        state="open",
        title="Add new feature"
    )

    ctx = ErkContext(git=git, github=github)
    runner = CliRunner()

    result = runner.invoke(list_cmd, [], obj=ctx)

    assert result.exit_code == 0
    assert "#123" in result.output
    assert "open" in result.output.lower() or "Open" in result.output
```

## Root Filtering

The list command can filter branches to show only root-level branches:

```python
def test_list_root_filtering() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=[
            "main",
            "feature/parent",
            "feature/parent/child",
            "other/branch"
        ]
    )

    runner = CliRunner()
    result = runner.invoke(list_cmd, ["--root-only"], obj=ctx)

    assert result.exit_code == 0
    assert "feature/parent" in result.output
    assert "other/branch" in result.output
    # Child should be filtered out
    assert "feature/parent/child" not in result.output
```

## Stack Hierarchy Display

Testing hierarchical stack display:

```python
def test_list_stack_hierarchy() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "level1", "level1/level2", "level1/level2/level3"]
    )

    graphite = FakeGraphite()
    graphite.add_stack("level1", ["level1/level2"])
    graphite.add_stack("level1/level2", ["level1/level2/level3"])

    ctx = ErkContext(git=git, graphite=graphite)
    runner = CliRunner()

    result = runner.invoke(list_cmd, ["--stacks"], obj=ctx)

    assert result.exit_code == 0
    # Verify tree structure characters
    assert "├──" in result.output or "└──" in result.output
    # Verify all levels present
    assert "level1" in result.output
    assert "level2" in result.output
    assert "level3" in result.output
```

## Trunk Detection

The list command detects and handles trunk branches (main, master, etc.):

```python
def test_list_trunk_detection() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "develop", "feature/test"]
    )

    runner = CliRunner()
    result = runner.invoke(list_cmd, [], obj=ctx)

    assert result.exit_code == 0
    # Trunk branches may be formatted differently or excluded
    # Verify feature branches shown
    assert "feature/test" in result.output
```

## Edge Cases

### No Branches

```python
def test_list_no_branches() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main"]  # Only trunk
    )

    runner = CliRunner()
    result = runner.invoke(list_cmd, [], obj=ctx)

    assert result.exit_code == 0
    assert "No branches" in result.output or "No workspaces" in result.output
```

### PR API Failures

```python
def test_list_github_api_failure() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature/test"]
    )

    github = FakeGitHub()
    github.set_error("API rate limit exceeded")

    ctx = ErkContext(git=git, github=github)
    runner = CliRunner()

    result = runner.invoke(list_cmd, [], obj=ctx)

    # Should handle gracefully, still show branches
    assert result.exit_code == 0
    assert "feature/test" in result.output
```

## Output Format Assertions

### Table Structure

```python
def test_list_table_format() -> None:
    # Verify table headers and alignment
    result = runner.invoke(list_cmd, [], obj=ctx)

    assert result.exit_code == 0
    # Check for table headers
    assert "Branch" in result.output or "Name" in result.output
    assert "PR" in result.output or "Pull Request" in result.output
```

### Color Coding

```python
def test_list_color_coding() -> None:
    from click import unstyle

    github = FakeGitHub()
    github.add_pr("feature/open", number=1, state="open")
    github.add_pr("feature/merged", number=2, state="merged")

    result = runner.invoke(list_cmd, [], obj=ctx)

    # Strip colors for reliable assertions
    clean = unstyle(result.output)
    assert "open" in clean.lower()
    assert "merged" in clean.lower()
```

## See Also

- [../CLAUDE.md](../CLAUDE.md) - Display command patterns
- [../../CLAUDE.md](../../CLAUDE.md) - General CLI command patterns
- [../../../docs/TESTING.md](../../../../docs/TESTING.md) - Complete testing guide
