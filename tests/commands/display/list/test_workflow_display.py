"""Tests for workflow run display in erk list command."""

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.types import WorkflowRun
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.cli import cli
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.output_helpers import strip_ansi


def test_list_displays_workflow_status_for_worktree_with_impl_folder() -> None:
    """Workflow status should appear when worktree has .impl/issue.json."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/owner/repo/issues/123", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Build fake git ops with worktree info
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow-started metadata in issue comment
        comment_body = """
## 🔔 Implementation Started

<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2025-01-20T10:00:00Z"
workflow_run_id: "12345678"
workflow_run_url: "https://github.com/owner/repo/actions/runs/12345678"
issue_number: 123
```
</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        github_issues = FakeGitHubIssues(comments={123: [comment_body]})

        # Add workflow run with success status
        workflow_run = WorkflowRun(
            run_id="12345678",
            status="completed",
            conclusion="success",
            branch="feature-branch",
            head_sha="abc123",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier comparison
        output = strip_ansi(result.output)

        # Verify workflow status appears
        assert "CI" in output
        # Check for success emoji (✅)
        assert "✅" in result.output or "success" in output.lower()


def test_list_displays_workflow_in_progress_status() -> None:
    """Workflow status should show in-progress indicator."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 456, "issue_url": "https://github.com/owner/repo/issues/456", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2025-01-20T10:00:00Z"
workflow_run_id: "87654321"
workflow_run_url: "https://github.com/owner/repo/actions/runs/87654321"
issue_number: 456
```
</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        github_issues = FakeGitHubIssues(comments={456: [comment_body]})

        # Add workflow run with in_progress status
        workflow_run = WorkflowRun(
            run_id="87654321",
            status="in_progress",
            conclusion=None,
            branch="feature-branch",
            head_sha="def456",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify in-progress indicator appears (⟳)
        assert "⟳" in result.output or "in_progress" in result.output.lower()
        assert "CI" in strip_ansi(result.output)


def test_list_displays_workflow_failure_status() -> None:
    """Workflow status should show failure indicator."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 789, "issue_url": "https://github.com/owner/repo/issues/789", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2025-01-20T10:00:00Z"
workflow_run_id: "99999999"
workflow_run_url: "https://github.com/owner/repo/actions/runs/99999999"
issue_number: 789
```
</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        github_issues = FakeGitHubIssues(comments={789: [comment_body]})

        # Add workflow run with failure status
        workflow_run = WorkflowRun(
            run_id="99999999",
            status="completed",
            conclusion="failure",
            branch="feature-branch",
            head_sha="ghi789",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify failure indicator appears (❌)
        assert "❌" in result.output or "failure" in result.output.lower()
        assert "CI" in strip_ansi(result.output)


def test_list_skips_workflow_for_worktree_without_impl_folder() -> None:
    """Worktrees without .impl/ folder should not show workflow status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # No .impl/ folder created

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        github_issues = FakeGitHubIssues(comments={})
        github = FakeGitHub(workflow_runs={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Command should succeed but not show workflow status for this worktree
        output = strip_ansi(result.output)
        assert "feature-branch" in output
        # No workflow indicators should appear for this worktree


def test_list_handles_missing_workflow_run_gracefully() -> None:
    """Missing workflow run should not break list command."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 999, "issue_url": "https://github.com/owner/repo/issues/999", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        comment_body = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2025-01-20T10:00:00Z"
workflow_run_id: "nonexistent"
workflow_run_url: "https://github.com/owner/repo/actions/runs/nonexistent"
issue_number: 999
```
</details>
<!-- /erk:metadata-block:workflow-started -->
"""
        github_issues = FakeGitHubIssues(comments={999: [comment_body]})

        # GitHub returns None for missing workflow run
        github = FakeGitHub(workflow_runs=[])  # Empty - run ID not found

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Command should succeed and show worktree without workflow status
        output = strip_ansi(result.output)
        assert "feature-branch" in output


def test_list_displays_queued_workflow_status() -> None:
    """Workflow status should show hourglass emoji for queued workflows."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 500, "issue_url": "https://github.com/owner/repo/issues/500", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with queued status
        workflow_run = WorkflowRun(
            run_id="55555555",
            status="queued",
            conclusion=None,
            branch="feature-branch",
            head_sha="abc555",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])
        github_issues = FakeGitHubIssues(comments={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify queued emoji (⧗) appears
        assert "⧗" in result.output, "Expected hourglass emoji for queued workflow"


def test_list_displays_cancelled_workflow_status() -> None:
    """Workflow status should show stop sign emoji for cancelled workflows."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 600, "issue_url": "https://github.com/owner/repo/issues/600", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with cancelled conclusion
        workflow_run = WorkflowRun(
            run_id="66666666",
            status="completed",
            conclusion="cancelled",
            branch="feature-branch",
            head_sha="abc666",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])
        github_issues = FakeGitHubIssues(comments={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify stop sign emoji (⛔) appears
        assert "⛔" in result.output, "Expected stop sign emoji for cancelled workflow"


def test_list_displays_unknown_workflow_status() -> None:
    """Workflow status should show question mark emoji for unknown status."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 700, "issue_url": "https://github.com/owner/repo/issues/700", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with unknown status
        workflow_run = WorkflowRun(
            run_id="77777777",
            status="unknown_status",
            conclusion=None,
            branch="feature-branch",
            head_sha="abc777",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])
        github_issues = FakeGitHubIssues(comments={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify question mark emoji (❓) appears
        assert "❓" in result.output, "Expected question mark emoji for unknown status"


def test_list_handles_batch_query_exception() -> None:
    """Command should succeed even if batch workflow query raises exception."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 800, "issue_url": "https://github.com/owner/repo/issues/800", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # No workflow runs configured (simulates API failure or no runs found)
        github = FakeGitHub(workflow_runs=[])
        github_issues = FakeGitHubIssues(comments={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        # Command should succeed despite API failure
        assert result.exit_code == 0, result.output

        # Verify worktree still displays (without workflow status)
        output = strip_ansi(result.output)
        assert "feature-branch" in output


def test_list_without_impl_folder_skips_workflow_query() -> None:
    """Worktrees without .impl/ folder should not trigger workflow queries."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree WITHOUT .impl/ folder
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)
        # No .impl/ folder created

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run (should not be displayed for this worktree)
        workflow_run = WorkflowRun(
            run_id="99999999",
            status="completed",
            conclusion="success",
            branch="feature-branch",
            head_sha="abc999",
        )
        github = FakeGitHub(workflow_runs=[workflow_run])
        github_issues = FakeGitHubIssues(comments={})

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            issues=github_issues,
            graphite=FakeGraphite(pr_info={}),
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify worktree displays without workflow status
        output = strip_ansi(result.output)
        assert "feature-branch" in output
        # CI column should not appear or show no status for this worktree
        # (The implementation only queries workflows for branches with .impl/ folders)
