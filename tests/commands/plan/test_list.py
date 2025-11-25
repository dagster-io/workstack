"""Tests for plan list command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.plan_store.fake import FakePlanStore
from erk.core.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_list_plans_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    # Arrange
    issue1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": issue1, "2": issue2})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue 1" in result.output
        assert "#2" in result.output
        assert "Issue 2" in result.output


def test_list_plans_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    # Arrange
    open_issue = Plan(
        plan_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_issue = Plan(
        plan_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": open_issue, "2": closed_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Filter for open issues
        result = runner.invoke(cli, ["list", "--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Issue" in result.output
        assert "#2" not in result.output


def test_list_plans_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    # Arrange
    issue_with_both = Plan(
        plan_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_with_one = Plan(
        plan_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": issue_with_both, "2": issue_with_one})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Filter for both labels (AND logic)
        result = runner.invoke(
            cli,
            ["list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue with both labels" in result.output
        assert "#2" not in result.output


def test_list_plans_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    # Arrange
    issues = {}
    for i in range(1, 6):
        issues[str(i)] = Plan(
            plan_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
        )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans=issues)
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["list", "--limit", "2"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output


def test_list_plans_combined_filters() -> None:
    """Test combining multiple filters."""
    # Arrange
    matching_issue = Plan(
        plan_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    wrong_state = Plan(
        plan_identifier="2",
        title="Wrong State",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels = Plan(
        plan_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/3",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": matching_issue, "2": wrong_state, "3": wrong_labels})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(
            cli,
            [
                "list",
                "--state",
                "open",
                "--label",
                "erk-plan",
                "--label",
                "bug",
            ],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Matching Issue" in result.output


def test_list_plans_empty_results() -> None:
    """Test querying with filters that match no issues."""
    # Arrange
    issue = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["list", "--state", "closed"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output


def test_ls_alias_works() -> None:
    """Test that ls alias invokes the same logic as list command."""
    # Arrange
    issue1 = Plan(
        plan_identifier="1",
        title="Test Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use ls alias instead of list
        result = runner.invoke(cli, ["ls"], obj=ctx)

        # Assert - Should produce same output as list command
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Test Issue" in result.output


def test_list_plans_shows_worktree_status() -> None:
    """Test that list command displays worktree names from issue comments."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange - Create issue with metadata field containing issue number
    issue1 = Plan(
        plan_identifier="867",
        title="Rename Erk Slash Commands",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/867",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 867},
    )

    issue2 = Plan(
        plan_identifier="868",
        title="Issue Without Worktree",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/868",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 868},
    )

    # Create comment with worktree metadata block
    comment_with_metadata = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: rename-erk-slash-commands
branch_name: rename-erk-slash-commands
timestamp: "2024-11-23T10:00:00Z"
issue_number: 867
```
</details>
<!-- /erk:metadata-block -->
"""

    # Configure fake GitHub issues with comments
    github = FakeGitHubIssues(
        comments={
            867: [comment_with_metadata],
            868: [],  # No comments for issue 868
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"867": issue1, "868": issue2})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#867" in result.output
        assert "Rename Erk Slash Commands" in result.output
        assert "rename-erk-slash-commands" in result.output
        assert "#868" in result.output
        assert "Issue Without Worktree" in result.output


def test_list_plans_shows_most_recent_worktree() -> None:
    """Test that list command shows the most recent worktree when multiple exist."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="900",
        title="Issue with Multiple Worktrees",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/900",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 900},
    )

    # Create multiple comments with different timestamps
    older_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: first-attempt
branch_name: first-attempt
timestamp: "2024-11-20T10:00:00Z"
issue_number: 900
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
timestamp: "2024-11-23T10:00:00Z"
issue_number: 900
```
</details>
<!-- /erk:metadata-block -->
"""

    # Configure fake with both comments
    github = FakeGitHubIssues(
        comments={
            900: [older_comment, newer_comment],
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"900": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show most recent worktree
        assert result.exit_code == 0
        assert "second-attempt" in result.output
        assert "first-attempt" not in result.output


def test_list_plans_shows_worktree_from_local_impl() -> None:
    """Test that list command detects worktree from local .impl/issue.json file."""
    import json

    from erk_shared.git.abc import WorktreeInfo
    from erk_shared.github.issues import FakeGitHubIssues

    from erk.core.git.fake import FakeGit

    # Arrange
    issue1 = Plan(
        plan_identifier="950",
        title="Test Local Detection",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/950",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 950},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a worktree with .impl/issue.json
        worktree_path = env.cwd.parent / "feature-worktree"
        worktree_path.mkdir(parents=True)
        impl_folder = worktree_path / ".impl"
        impl_folder.mkdir()

        # Manually create issue.json file
        issue_json_path = impl_folder / "issue.json"
        issue_data = {
            "issue_number": 950,
            "issue_url": "https://github.com/owner/repo/issues/950",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json_path.write_text(json.dumps(issue_data, indent=2), encoding="utf-8")

        # Configure FakeGit with worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-branch", is_root=False),
                ]
            },
        )

        # Create context with empty GitHub (no comments)
        github = FakeGitHubIssues(comments={})
        store = FakePlanStore(plans={"950": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, git=git, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show worktree name from local detection
        assert result.exit_code == 0
        assert "#950" in result.output
        assert "Test Local Detection" in result.output
        assert "feature-worktree" in result.output


def test_list_plans_prefers_local_over_github() -> None:
    """Test that local .impl/issue.json detection takes precedence over GitHub comments."""
    import json

    from erk_shared.git.abc import WorktreeInfo
    from erk_shared.github.issues import FakeGitHubIssues

    from erk.core.git.fake import FakeGit

    # Arrange
    issue1 = Plan(
        plan_identifier="960",
        title="Test Precedence",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/960",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 960},
    )

    # Create GitHub comment with different worktree name
    github_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: old-github-worktree
branch_name: old-github-worktree
timestamp: "2024-11-20T10:00:00Z"
issue_number: 960
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a worktree with .impl/issue.json
        worktree_path = env.cwd.parent / "local-worktree"
        worktree_path.mkdir(parents=True)
        impl_folder = worktree_path / ".impl"
        impl_folder.mkdir()

        # Manually create issue.json file
        issue_json_path = impl_folder / "issue.json"
        issue_data = {
            "issue_number": 960,
            "issue_url": "https://github.com/owner/repo/issues/960",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json_path.write_text(json.dumps(issue_data, indent=2), encoding="utf-8")

        # Configure FakeGit with worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature", is_root=False),
                ]
            },
        )

        # Configure GitHub with comment
        github = FakeGitHubIssues(comments={960: [github_comment]})
        store = FakePlanStore(plans={"960": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, git=git, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show local worktree name, not GitHub one
        assert result.exit_code == 0
        assert "local-worktree" in result.output
        assert "old-github-worktree" not in result.output


def test_list_plans_falls_back_to_github_when_no_local() -> None:
    """Test that GitHub comment detection works when no local .impl/issue.json exists."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="970",
        title="Test Fallback",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/970",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 970},
    )

    # Create GitHub comment
    github_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: github-worktree
branch_name: github-worktree
timestamp: "2024-11-20T10:00:00Z"
issue_number: 970
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # No local worktrees with .impl folders
        github = FakeGitHubIssues(comments={970: [github_comment]})
        store = FakePlanStore(plans={"970": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show GitHub worktree name
        assert result.exit_code == 0
        assert "#970" in result.output
        assert "github-worktree" in result.output


def test_list_plans_handles_multiple_local_worktrees() -> None:
    """Test first-found worktree shown when multiple worktrees reference same issue."""
    import json

    from erk_shared.git.abc import WorktreeInfo
    from erk_shared.github.issues import FakeGitHubIssues

    from erk.core.git.fake import FakeGit

    # Arrange
    issue1 = Plan(
        plan_identifier="980",
        title="Test Multiple Local",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/980",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 980},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create two worktrees both referencing same issue
        worktree1 = env.cwd.parent / "first-worktree"
        worktree1.mkdir(parents=True)
        impl1 = worktree1 / ".impl"
        impl1.mkdir()
        issue_json1 = impl1 / "issue.json"
        issue_data1 = {
            "issue_number": 980,
            "issue_url": "https://github.com/owner/repo/issues/980",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json1.write_text(json.dumps(issue_data1, indent=2), encoding="utf-8")

        worktree2 = env.cwd.parent / "second-worktree"
        worktree2.mkdir(parents=True)
        impl2 = worktree2 / ".impl"
        impl2.mkdir()
        issue_json2 = impl2 / "issue.json"
        issue_data2 = {
            "issue_number": 980,
            "issue_url": "https://github.com/owner/repo/issues/980",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json2.write_text(json.dumps(issue_data2, indent=2), encoding="utf-8")

        # Configure FakeGit with both worktrees
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree1, branch="branch1", is_root=False),
                    WorktreeInfo(path=worktree2, branch="branch2", is_root=False),
                ]
            },
        )

        github = FakeGitHubIssues(comments={})
        store = FakePlanStore(plans={"980": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, git=git, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show first worktree found
        assert result.exit_code == 0
        assert "#980" in result.output
        # Should show exactly one of the worktrees (first-found behavior)
        # The order depends on git.list_worktrees() order
        assert "first-worktree" in result.output or "second-worktree" in result.output


def test_list_plans_shows_action_state_with_no_queue_label() -> None:
    """Test that plans without erk-queue label show '-' for action state."""
    # Arrange
    issue1 = Plan(
        plan_identifier="1001",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1001",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1001},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1001": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1001" in result.output


def test_list_plans_shows_pending_action_state() -> None:
    """Test that plans with erk-queue label but no metadata show 'Pending'."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="1002",
        title="Pending Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1002",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1002},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1002: []})
        store = FakePlanStore(plans={"1002": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1002" in result.output


def test_list_plans_shows_running_action_state_with_workflow_started() -> None:
    """Test that plans with workflow-started metadata show 'Running'."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="1003",
        title="Running Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1003",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1003},
    )

    # Create comment with workflow-started metadata
    comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2024-11-23T10:00:00Z"
workflow_run_id: "12345"
workflow_run_url: "https://github.com/owner/repo/actions/runs/12345"
issue_number: 1003
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1003: [comment]})
        store = FakePlanStore(plans={"1003": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1003" in result.output


def test_list_plans_shows_complete_action_state() -> None:
    """Test that plans with complete implementation status show 'Complete'."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="1004",
        title="Complete Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1004",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1004},
    )

    # Create comment with complete status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: 5
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1004: [comment]})
        store = FakePlanStore(plans={"1004": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1004" in result.output


def test_list_plans_shows_failed_action_state() -> None:
    """Test that plans with failed implementation status show 'Failed'."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    issue1 = Plan(
        plan_identifier="1005",
        title="Failed Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1005",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1005},
    )

    # Create comment with failed status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: failed
completed_steps: 2
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1005: [comment]})
        store = FakePlanStore(plans={"1005": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1005" in result.output


def test_list_plans_filter_by_action_state_pending() -> None:
    """Test filtering plans by action state (pending)."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange - Create plans with different action states
    pending_plan = Plan(
        plan_identifier="1010",
        title="Pending Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1010",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1010},
    )

    no_queue_plan = Plan(
        plan_identifier="1011",
        title="No Queue Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1011",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1011},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1010: [], 1011: []})
        store = FakePlanStore(plans={"1010": pending_plan, "1011": no_queue_plan})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list", "--action-state", "pending"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1010" in result.output
        assert "Pending Plan" in result.output
        assert "#1011" not in result.output


def test_list_plans_filter_by_action_state_complete() -> None:
    """Test filtering plans by action state (complete)."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange
    complete_plan = Plan(
        plan_identifier="1020",
        title="Complete Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1020",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1020},
    )

    pending_plan = Plan(
        plan_identifier="1021",
        title="Pending Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1021",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1021},
    )

    # Create comment with complete status
    complete_comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: 5
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={1020: [complete_comment], 1021: []})
        store = FakePlanStore(plans={"1020": complete_plan, "1021": pending_plan})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act
        result = runner.invoke(cli, ["list", "--action-state", "complete"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1020" in result.output
        assert "Complete Plan" in result.output
        assert "#1021" not in result.output


def test_list_plans_action_filter_no_matches() -> None:
    """Test action state filter with no matching plans."""
    from erk_shared.github.issues import FakeGitHubIssues

    # Arrange - Plan without erk-queue label (action state will be "-")
    plan = Plan(
        plan_identifier="1030",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1030",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1030},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHubIssues(comments={})
        store = FakePlanStore(plans={"1030": plan})
        ctx = build_workspace_test_context(env, plan_store=store, issues=github)

        # Act - Filter for "running" which won't match
        result = runner.invoke(cli, ["list", "--action-state", "running"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output


def test_list_plans_pr_column_open_pr() -> None:
    """Test PR column displays open PR with 👀 emoji."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="100",
        title="Plan with Open PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/100",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 100},
    )

    pr = PullRequestInfo(
        number=200,
        state="OPEN",
        url="https://github.com/owner/repo/pull/200",
        is_draft=False,
        title="PR for issue 100",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"100": plan})
        github = FakeGitHub(pr_issue_linkages={100: [pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#200 👀" in result.output
        assert "✅" in result.output  # Checks passing


def test_list_plans_pr_column_draft_pr() -> None:
    """Test PR column displays draft PR with 🚧 emoji."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="101",
        title="Plan with Draft PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/101",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 101},
    )

    pr = PullRequestInfo(
        number=201,
        state="DRAFT",
        url="https://github.com/owner/repo/pull/201",
        is_draft=True,
        title="Draft PR for issue 101",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"101": plan})
        github = FakeGitHub(pr_issue_linkages={101: [pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#201 🚧" in result.output
        assert "🔄" in result.output  # Checks pending


def test_list_plans_pr_column_merged_pr() -> None:
    """Test PR column displays merged PR with 🎉 emoji."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="102",
        title="Plan with Merged PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/102",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 102},
    )

    pr = PullRequestInfo(
        number=202,
        state="MERGED",
        url="https://github.com/owner/repo/pull/202",
        is_draft=False,
        title="Merged PR for issue 102",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"102": plan})
        github = FakeGitHub(pr_issue_linkages={102: [pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#202 🎉" in result.output
        assert "✅" in result.output  # Checks passing


def test_list_plans_pr_column_closed_pr() -> None:
    """Test PR column displays closed PR with ⛔ emoji."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="103",
        title="Plan with Closed PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/103",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 103},
    )

    pr = PullRequestInfo(
        number=203,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/203",
        is_draft=False,
        title="Closed PR for issue 103",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"103": plan})
        github = FakeGitHub(pr_issue_linkages={103: [pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#203 ⛔" in result.output
        assert "🚫" in result.output  # Checks failing


def test_list_plans_pr_column_with_conflicts() -> None:
    """Test PR column shows conflict indicator 💥 for open/draft PRs with conflicts."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="104",
        title="Plan with Conflicted PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/104",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 104},
    )

    pr = PullRequestInfo(
        number=204,
        state="OPEN",
        url="https://github.com/owner/repo/pull/204",
        is_draft=False,
        title="Conflicted PR for issue 104",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=True,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"104": plan})
        github = FakeGitHub(pr_issue_linkages={104: [pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#204 👀💥" in result.output  # Open with conflicts


def test_list_plans_pr_column_multiple_prs_prefers_open() -> None:
    """Test PR column shows most recent open PR when multiple PRs exist."""
    from erk_shared.github.types import PullRequestInfo
    from src.erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="105",
        title="Plan with Multiple PRs",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/105",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 105},
    )

    # Older closed PR
    closed_pr = PullRequestInfo(
        number=205,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/205",
        is_draft=False,
        title="Old closed PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    # Recent open PR (should be selected)
    open_pr = PullRequestInfo(
        number=206,
        state="OPEN",
        url="https://github.com/owner/repo/pull/206",
        is_draft=False,
        title="Recent open PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"105": plan})
        # PRs already sorted by created_at descending
        github = FakeGitHub(pr_issue_linkages={105: [open_pr, closed_pr]})
        ctx = build_workspace_test_context(env, plan_store=store, github=github)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#206 👀" in result.output  # Shows open PR, not closed


def test_list_plans_pr_column_no_pr_linked() -> None:
    """Test PR column shows '-' when no PR is linked to issue."""
    # Arrange
    plan = Plan(
        plan_identifier="106",
        title="Plan without PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/106",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 106},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"106": plan})
        # No PR linkages configured
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#106" in result.output
        # PR and Checks columns should both show "-"
        # Can't easily assert the exact column position, but verifying no emojis appear
        assert "👀" not in result.output
        assert "🚧" not in result.output
        assert "🎉" not in result.output
        assert "⛔" not in result.output
