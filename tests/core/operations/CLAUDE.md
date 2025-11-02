# Operations Testing Patterns

## Overview

This directory contains tests for the operations layer - the abstraction over git, Graphite, and GitHub. All tests use fake implementations with mutation tracking instead of mocks.

## Test Files in This Directory

- `test_gitops_unit.py` - Git operations (branch, checkout, delete)
- `test_graphite_ops.py` - Graphite stack operations
- `test_github_ops.py` - GitHub API operations (PRs, issues)

## Core Principle: Fakes, Not Mocks

**NEVER use unittest.mock or pytest mocking for operations tests.**

Instead:

- Use `FakeGitOps`, `FakeGraphiteOps`, `FakeGitHubOps`
- Track mutations via read-only properties
- Configure state at construction time

## FakeGitOps Usage

### Basic Setup

```python
from tests.fakes.fake_gitops import FakeGitOps

def test_git_operation() -> None:
    # Arrange: Configure initial state
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "feature/existing"],
        remote_tracking={"main": "origin/main"}
    )

    # Act: Perform operation
    git_ops.create_branch("feature/new")

    # Assert: Verify via read-only property
    assert "feature/new" in git_ops.created_branches
```

### Read-Only Properties for Mutation Tracking

```python
# Available read-only properties on FakeGitOps:
git_ops.created_branches  # Set[str] - branches created
git_ops.deleted_branches  # Set[str] - branches deleted
git_ops.checked_out_branches  # list[str] - checkout history
git_ops.rename_history  # list[tuple[str, str]] - (old, new) pairs
git_ops.pushed_branches  # Set[str] - branches pushed to remote
```

### Example: Testing Branch Creation

```python
def test_create_branch() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main"]
    )

    # Create new branch
    git_ops.create_branch("feature/test")

    # Verify creation
    assert "feature/test" in git_ops.created_branches
    assert "feature/test" in git_ops.all_branches  # Updated state
```

### Example: Testing Branch Deletion

```python
def test_delete_branch() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "old-branch"]
    )

    # Delete branch
    git_ops.delete_branch("old-branch")

    # Verify deletion
    assert "old-branch" in git_ops.deleted_branches
    assert "old-branch" not in git_ops.all_branches
```

### Example: Testing Branch Rename

```python
def test_rename_branch() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "old-name"]
    )

    # Rename branch
    git_ops.rename_branch("old-name", "new-name")

    # Verify rename
    assert git_ops.rename_history == [("old-name", "new-name")]
    assert "old-name" not in git_ops.all_branches
    assert "new-name" in git_ops.all_branches
```

### Example: Testing Checkout

```python
def test_checkout_branch() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    # Checkout branch
    git_ops.checkout("feature")

    # Verify checkout
    assert git_ops.current_branch == "feature"
    assert "feature" in git_ops.checked_out_branches
```

## FakeGraphiteOps Usage

### Basic Setup

```python
from tests.fakes.fake_graphite_ops import FakeGraphiteOps

def test_graphite_operation() -> None:
    graphite_ops = FakeGraphiteOps()

    # Add stack relationships
    graphite_ops.add_stack("parent", ["child1", "child2"])

    # Verify
    assert graphite_ops.get_children("parent") == ["child1", "child2"]
```

### Read-Only Properties

```python
# Available read-only properties on FakeGraphiteOps:
graphite_ops.renamed_stacks  # list[tuple[str, str]] - renamed stacks
graphite_ops.deleted_stacks  # Set[str] - deleted stack names
```

### Example: Testing Stack Rename

```python
def test_rename_stack() -> None:
    graphite_ops = FakeGraphiteOps()
    graphite_ops.add_stack("old-name", ["child"])

    # Rename stack
    graphite_ops.rename_stack("old-name", "new-name")

    # Verify rename
    assert graphite_ops.renamed_stacks == [("old-name", "new-name")]
    assert graphite_ops.get_children("new-name") == ["child"]
```

### Example: Testing Stack Hierarchy

```python
def test_stack_hierarchy() -> None:
    graphite_ops = FakeGraphiteOps()

    # Build multi-level stack
    graphite_ops.add_stack("level1", ["level2"])
    graphite_ops.add_stack("level2", ["level3"])

    # Verify hierarchy
    assert graphite_ops.get_children("level1") == ["level2"]
    assert graphite_ops.get_children("level2") == ["level3"]
    assert graphite_ops.get_parent("level2") == "level1"
    assert graphite_ops.get_parent("level3") == "level2"
```

## FakeGitHubOps Usage

### Basic Setup

```python
from tests.fakes.fake_github_ops import FakeGitHubOps

def test_github_operation() -> None:
    github_ops = FakeGitHubOps()

    # Add PR data
    github_ops.add_pr(
        "feature/branch",
        number=123,
        state="open",
        title="Add feature",
        url="https://github.com/org/repo/pull/123"
    )

    # Query PR
    pr = github_ops.get_pr("feature/branch")
    assert pr.number == 123
    assert pr.state == "open"
```

### Read-Only Properties

```python
# Available read-only properties on FakeGitHubOps:
github_ops.created_prs  # list[dict] - PRs created during test
github_ops.closed_prs  # list[int] - PR numbers closed
github_ops.api_calls  # list[str] - API endpoints called
```

### Example: Testing PR Creation

```python
def test_create_pr() -> None:
    github_ops = FakeGitHubOps()

    # Create PR
    pr = github_ops.create_pr(
        head="feature/branch",
        base="main",
        title="New feature",
        body="Description"
    )

    # Verify creation
    assert len(github_ops.created_prs) == 1
    assert github_ops.created_prs[0]["head"] == "feature/branch"
    assert github_ops.created_prs[0]["title"] == "New feature"
```

### Example: Testing API Failures

```python
def test_github_api_failure() -> None:
    github_ops = FakeGitHubOps()

    # Configure error
    github_ops.set_error("API rate limit exceeded")

    # Operation should handle error
    with pytest.raises(GitHubAPIError) as exc_info:
        github_ops.get_pr("feature/branch")

    assert "rate limit" in str(exc_info.value)
```

## Testing Complex Scenarios

### Multi-Operation Sequences

```python
def test_complex_workflow() -> None:
    git_ops = FakeGitOps(current_branch="main", all_branches=["main"])
    graphite_ops = FakeGraphiteOps()

    # Create branch
    git_ops.create_branch("parent")
    git_ops.checkout("parent")

    # Create child branch and stack
    git_ops.create_branch("parent/child")
    graphite_ops.add_stack("parent", ["parent/child"])

    # Verify entire workflow
    assert "parent" in git_ops.created_branches
    assert "parent/child" in git_ops.created_branches
    assert git_ops.current_branch == "parent/child"
    assert graphite_ops.get_children("parent") == ["parent/child"]
```

### Testing Error Conditions

```python
def test_error_handling() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "existing"]
    )

    # Attempting to create duplicate should raise error
    with pytest.raises(BranchExistsError):
        git_ops.create_branch("existing")

    # Verify no mutation occurred
    assert len(git_ops.created_branches) == 0
```

## Common Patterns

### Verifying No Side Effects

```python
def test_read_only_operation() -> None:
    git_ops = FakeGitOps(current_branch="main", all_branches=["main", "feature"])

    # Read-only query
    branches = git_ops.get_all_branches()

    # Verify no mutations
    assert len(git_ops.created_branches) == 0
    assert len(git_ops.deleted_branches) == 0
    assert branches == ["main", "feature"]
```

### Testing State Transitions

```python
def test_state_transition() -> None:
    git_ops = FakeGitOps(current_branch="main", all_branches=["main"])

    # Initial state
    assert git_ops.current_branch == "main"

    # Transition
    git_ops.create_branch("feature")
    git_ops.checkout("feature")

    # Final state
    assert git_ops.current_branch == "feature"
    assert "feature" in git_ops.checked_out_branches
```

## Why Fakes Over Mocks

### Problems with Mocks

```python
# ❌ DON'T: Use mocks
from unittest.mock import Mock, patch

git_ops = Mock()
git_ops.create_branch = Mock()

# Fragile - tests implementation, not behavior
git_ops.create_branch.assert_called_once_with("branch-name")
```

### Benefits of Fakes

```python
# ✅ DO: Use fakes
git_ops = FakeGitOps(current_branch="main")

# Robust - tests actual behavior
git_ops.create_branch("branch-name")
assert "branch-name" in git_ops.created_branches
```

Fakes provide:

1. **Real behavior**: Fakes implement actual logic
2. **State tracking**: Read-only properties track mutations
3. **Type safety**: Fakes implement the same ABC as real implementations
4. **Refactor-proof**: Tests survive implementation changes

## See Also

- [../CLAUDE.md](../CLAUDE.md) - Core testing patterns
- [../../fakes/](../../fakes/) - Fake implementations
- [../../docs/TESTING.md](../../../docs/TESTING.md#dependency-categories) - Dependency categories
