"""Unit tests for get_worktree_status helper function."""

from pathlib import Path

from erk.cli.commands.plan_issue.list_cmd import get_worktree_status
from erk.core.github.issues import FakeGitHubIssues


def test_get_worktree_status_with_single_worktree() -> None:
    """Test extracting worktree name from issue comments."""
    # Arrange
    comment_with_metadata = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: test-worktree
branch_name: test-branch
timestamp: "2024-11-23T10:00:00Z"
issue_number: 123
```
</details>
<!-- /erk:metadata-block -->
"""

    github = FakeGitHubIssues(
        comments={
            123: [comment_with_metadata],
        }
    )

    # Act
    worktree_name = get_worktree_status(github, Path("/fake/repo"), 123)

    # Assert
    assert worktree_name == "test-worktree"


def test_get_worktree_status_with_no_comments() -> None:
    """Test that None is returned when issue has no comments."""
    # Arrange
    github = FakeGitHubIssues(comments={})

    # Act
    worktree_name = get_worktree_status(github, Path("/fake/repo"), 456)

    # Assert
    assert worktree_name is None


def test_get_worktree_status_with_multiple_worktrees() -> None:
    """Test that most recent worktree is returned when multiple exist."""
    # Arrange
    older_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: first-attempt
branch_name: first-attempt
timestamp: "2024-11-20T10:00:00Z"
issue_number: 789
```
</details>
<!-- /erk:metadata-block -->
"""

    newer_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: second-attempt
branch_name: second-attempt
timestamp: "2024-11-23T15:00:00Z"
issue_number: 789
```
</details>
<!-- /erk:metadata-block -->
"""

    github = FakeGitHubIssues(
        comments={
            789: [older_comment, newer_comment],
        }
    )

    # Act
    worktree_name = get_worktree_status(github, Path("/fake/repo"), 789)

    # Assert
    assert worktree_name == "second-attempt"


def test_get_worktree_status_with_comments_but_no_metadata() -> None:
    """Test that None is returned when comments exist but have no worktree metadata."""
    # Arrange
    regular_comment = "This is a regular comment without metadata."

    github = FakeGitHubIssues(
        comments={
            999: [regular_comment],
        }
    )

    # Act
    worktree_name = get_worktree_status(github, Path("/fake/repo"), 999)

    # Assert
    assert worktree_name is None
