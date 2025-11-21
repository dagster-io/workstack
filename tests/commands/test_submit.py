"""Tests for erk submit command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk.core.plan_folder import create_plan_folder
from erk.core.repo_discovery import RepoContext
from tests.fakes.context import create_test_context
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub


def test_submit_errors_without_plan_folder(tmp_path: Path) -> None:
    """Test submit shows error when no .plan/ folder exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "No .plan/ folder found" in result.output


def test_submit_dry_run_shows_operations(tmp_path: Path) -> None:
    """Test dry-run shows what would happen."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .plan/ folder
    plan_content = "# Test Plan\n\n1. Step one"
    create_plan_folder(repo_root, plan_content)

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Would copy .plan/ to .submission/" in result.output
    assert "Would commit and push .submission/" in result.output
    assert "Would trigger GitHub Actions workflow" in result.output
    assert len(fake_github.triggered_workflows) == 0


def test_submit_errors_with_existing_submission(tmp_path: Path) -> None:
    """Test submit errors when .submission/ already exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create both .plan/ and .submission/
    plan_content = "# Test Plan\n\n1. Step one"
    create_plan_folder(repo_root, plan_content)
    (repo_root / ".submission").mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert ".submission/ folder already exists" in result.output


def test_submit_errors_on_detached_head(tmp_path: Path) -> None:
    """Test submit errors when in detached HEAD state."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .plan/ folder
    plan_content = "# Test Plan\n\n1. Step one"
    create_plan_folder(repo_root, plan_content)

    # No current branch (detached HEAD)
    fake_git = FakeGit(current_branches={repo_root: None})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "Not on a branch" in result.output


def test_submit_displays_run_id_and_commands(tmp_path: Path, monkeypatch) -> None:
    """Test submit displays run ID and copy-paste ready commands."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .plan/ folder
    plan_content = "# Test Plan\n\n1. Step one"
    create_plan_folder(repo_root, plan_content)

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    # Mock subprocess calls (git add, git commit, git push)
    import subprocess

    mock_run_calls = []

    def mock_run(*args, **kwargs):
        mock_run_calls.append((args, kwargs))
        # Create a successful result
        result = subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    # Verify success
    assert result.exit_code == 0

    # Verify run ID appears in output
    assert "Run ID: 1234567890" in result.output

    # Verify both monitoring commands are shown with run ID
    assert "gh run view 1234567890 --web" in result.output
    assert "gh run watch 1234567890" in result.output

    # Verify "View in browser" and "Monitor in terminal" headers
    assert "View in browser:" in result.output
    assert "Monitor in terminal:" in result.output

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "implement-plan.yml"
    assert inputs == {"branch-name": "feature-branch"}
