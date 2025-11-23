"""Tests for erk create command output behavior."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.cli import cli
from erk.core.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_create_from_current_branch_outputs_script_path_to_stdout() -> None:
    """Test that create --from-current-branch outputs script path to stdout, not stderr.

    This test verifies that the shell integration handler can read the script path
    from stdout. If the script path is written to stderr, the handler will miss it
    and display 'no directory change needed' instead of switching to the new worktree.

    See: https://github.com/anthropics/erk/issues/XXX
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch with --script flag
        result = runner.invoke(
            cli,
            ["create", "--from-current-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Script path is in stdout (for shell integration)
        assert result.stdout.strip() != "", (
            "Script path should be in stdout for shell integration to read. "
            "Currently it's being written to stderr via user_output(), "
            "but should be written to stdout via machine_output()."
        )

        # Assert: Script path is a valid path to activation script
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None, "Script path should reference a valid script"

        # Assert: Script contains cd command to new worktree
        expected_worktree_path = repo_dir / "worktrees" / "my-feature"
        assert str(expected_worktree_path) in script_content, (
            f"Script should cd to {expected_worktree_path}"
        )


def test_create_from_issue_with_valid_issue() -> None:
    """Test erk create --from-issue with valid erk-plan issue."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                123: IssueInfo(
                    number=123,
                    title="Add User Authentication",
                    body="## Implementation\n\n- Step 1\n- Step 2",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/123",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Run create --from-issue 123
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "123"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Worktree created with sanitized name (with date suffix for plan-derived)
        worktrees_dir = repo_dir / "worktrees"
        # Check that a worktree starting with the expected name exists
        worktree_dirs = list(worktrees_dir.glob("add-user-authentication*"))
        assert len(worktree_dirs) == 1, (
            f"Expected one worktree matching 'add-user-authentication*', found {worktree_dirs}"
        )
        expected_worktree_path = worktree_dirs[0]
        assert expected_worktree_path.exists()

        # Assert: .impl/ folder exists with correct content
        impl_path = expected_worktree_path / ".impl"
        assert impl_path.exists()

        # Assert: plan.md has issue body
        plan_path = impl_path / "plan.md"
        assert plan_path.exists()
        plan_content = plan_path.read_text(encoding="utf-8")
        assert "## Implementation" in plan_content

        # Assert: issue.json has metadata
        issue_json_path = impl_path / "issue.json"
        assert issue_json_path.exists()
        import json

        issue_json = json.loads(issue_json_path.read_text(encoding="utf-8"))
        assert issue_json["number"] == 123
        assert issue_json["title"] == "Add User Authentication"
        assert issue_json["url"] == "https://github.com/owner/repo/issues/123"


def test_create_from_issue_missing_label() -> None:
    """Test erk create --from-issue fails if issue lacks erk-plan label."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue without erk-plan label
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                456: IssueInfo(
                    number=456,
                    title="Regular Issue",
                    body="Not a plan",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/456",
                    labels=["bug", "enhancement"],  # No erk-plan label
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Run create --from-issue 456
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "456"],
            obj=test_ctx,
        )

        # Assert: Error message about missing label
        assert result.exit_code == 1
        assert "must have 'erk-plan' label" in result.output
        assert "gh issue edit 456 --add-label erk-plan" in result.output


def test_create_from_issue_url_parsing() -> None:
    """Test erk create --from-issue with GitHub URL."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                789: IssueInfo(
                    number=789,
                    title="Feature Request",
                    body="Plan content",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/789",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Run with full GitHub URL
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "https://github.com/owner/repo/issues/789"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Success (URL parsed correctly)
        assert result.exit_code == 0
        assert "Created worktree" in result.output or "feature-request" in result.output


def test_create_from_issue_name_derivation() -> None:
    """Test worktree name derived from issue title."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue with special characters in title
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                111: IssueInfo(
                    number=111,
                    title="Fix: Database Connection Issues!!!",
                    body="Plan",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/111",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "111"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Name sanitized correctly (with date suffix for plan-derived)
        assert result.exit_code == 0
        worktrees_dir = repo_dir / "worktrees"
        # Check that a worktree starting with the expected name exists
        worktree_dirs = list(worktrees_dir.glob("fix-database-connection-issues*"))
        assert len(worktree_dirs) == 1, (
            "Expected one worktree matching 'fix-database-connection-issues*'"
        )
        assert worktree_dirs[0].exists()


def test_create_from_issue_not_found() -> None:
    """Test erk create --from-issue when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with no issues
        fake_issues = FakeGitHubIssues()  # Empty

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Request non-existent issue
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "999"],
            obj=test_ctx,
        )

        # Assert: Error from integration layer
        assert result.exit_code == 1
        # FakeGitHubIssues raises RuntimeError with "not found" message
        assert "not found" in result.output.lower() or "Issue #999" in result.output


def test_create_from_issue_readonly_operation() -> None:
    """Test that --from-issue doesn't create/modify issues."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                222: IssueInfo(
                    number=222,
                    title="Test",
                    body="Body",
                    state="OPEN",
                    url="https://example.com",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act
        result = runner.invoke(
            cli,
            ["create", "--from-issue", "222"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: No issues created
        assert len(fake_issues.created_issues) == 0
        # Assert: No comments added
        assert len(fake_issues.added_comments) == 0
