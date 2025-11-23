"""Tests for unified implement command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.implement import _detect_target_type, implement
from erk.core.plan_issue_store import FakePlanIssueStore, PlanIssue, PlanIssueState
from tests.fakes.git import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _create_sample_plan_issue(issue_number: str = "42") -> PlanIssue:
    """Create a sample plan issue for testing."""
    return PlanIssue(
        plan_issue_identifier=issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        state=PlanIssueState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )


# Target Detection Tests


def test_detect_issue_number_with_hash() -> None:
    """Test detection of issue numbers with # prefix."""
    target_info = _detect_target_type("#123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_plain_number_as_issue() -> None:
    """Test that plain numbers are treated as GitHub issue numbers."""
    target_info = _detect_target_type("123")
    assert target_info.target_type == "issue_number"
    assert target_info.issue_number == "123"


def test_detect_issue_url() -> None:
    """Test detection of GitHub issue URLs."""
    url = "https://github.com/user/repo/issues/456"
    target_info = _detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "456"


def test_detect_issue_url_with_path() -> None:
    """Test detection of GitHub issue URLs with additional path."""
    url = "https://github.com/user/repo/issues/789#issuecomment-123"
    target_info = _detect_target_type(url)
    assert target_info.target_type == "issue_url"
    assert target_info.issue_number == "789"


def test_detect_relative_numeric_file() -> None:
    """Test that numeric files with ./ prefix are treated as file paths."""
    target_info = _detect_target_type("./123")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_plain_and_prefixed_numbers_equivalent() -> None:
    """Test that plain and prefixed numbers both resolve to issue numbers."""
    result_plain = _detect_target_type("809")
    result_prefixed = _detect_target_type("#809")
    assert result_plain.target_type == result_prefixed.target_type == "issue_number"
    assert result_plain.issue_number == result_prefixed.issue_number == "809"


def test_detect_file_path() -> None:
    """Test detection of file paths."""
    target_info = _detect_target_type("./my-feature-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


def test_detect_file_path_with_special_chars() -> None:
    """Test detection of file paths with special characters."""
    target_info = _detect_target_type("/path/to/my-plan.md")
    assert target_info.target_type == "file_path"
    assert target_info.issue_number is None


# GitHub Issue Mode Tests


def test_implement_from_plain_issue_number() -> None:
    """Test implementing from GitHub issue number without # prefix."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"123": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Test with plain number (no # prefix)
        result = runner.invoke(implement, ["123"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "add-authentication-feature" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with correct issue number
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        issue_json_path = worktree_paths[0] / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


# GitHub Issue Mode Tests


def test_implement_from_issue_number() -> None:
    """Test implementing from GitHub issue number with # prefix."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "add-authentication-feature" in result.output

        # Verify worktree was created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_path = worktree_paths[0] / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "progress.md").exists()
        assert (impl_path / "issue.json").exists()


def test_implement_from_issue_url() -> None:
    """Test implementing from GitHub issue URL."""
    plan_issue = _create_sample_plan_issue("123")

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"123": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        url = "https://github.com/owner/repo/issues/123"
        result = runner.invoke(implement, [url], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert len(git.added_worktrees) == 1

        # Verify issue.json contains correct issue number
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        issue_json_path = worktree_paths[0] / ".impl" / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 123' in issue_json_content


def test_implement_from_issue_with_custom_name() -> None:
    """Test implementing from issue with custom worktree name."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--worktree-name", "my-custom-feature"], obj=ctx)

        assert result.exit_code == 0
        assert "my-custom-feature" in result.output

        worktree_path, _ = git.added_worktrees[0]
        assert "my-custom-feature" in str(worktree_path)


def test_implement_from_issue_fails_without_erk_plan_label() -> None:
    """Test that command fails when issue doesn't have erk-plan label."""
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Regular Issue",
        body="Not a plan issue",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["bug"],  # Missing "erk-plan" label
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "erk-plan" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_issue_fails_when_not_found() -> None:
    """Test that command fails when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#999"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_issue_dry_run() -> None:
    """Test dry-run mode for issue implementation."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert "Add Authentication Feature" in result.output
        assert len(git.added_worktrees) == 0


# Plan File Mode Tests


def test_implement_from_plan_file() -> None:
    """Test implementing from plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_content = "# Implementation Plan\n\nImplement feature X."
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text(plan_content, encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "my-feature" in result.output

        # Verify worktree created
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with plan content
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        impl_plan = worktree_paths[0] / ".impl" / "plan.md"
        assert impl_plan.exists()
        assert impl_plan.read_text(encoding="utf-8") == plan_content

        # Verify original plan file deleted (move semantics)
        assert not plan_file.exists()


def test_implement_from_plan_file_with_custom_name() -> None:
    """Test implementing from plan file with custom worktree name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(
            implement, [str(plan_file), "--worktree-name", "custom-name"], obj=ctx
        )

        assert result.exit_code == 0
        assert "custom-name" in result.output

        worktree_path, _ = git.added_worktrees[0]
        assert "custom-name" in str(worktree_path)


def test_implement_from_plan_file_strips_plan_suffix() -> None:
    """Test that '-plan' suffix is stripped from plan filenames."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file with -plan suffix
        plan_file = env.cwd / "authentication-feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file)], obj=ctx)

        assert result.exit_code == 0
        # Verify -plan suffix was stripped
        assert "authentication-feature" in result.output
        # Ensure no "-plan" in worktree name
        worktree_path, _ = git.added_worktrees[0]
        worktree_name = str(worktree_path.name)
        assert "-plan" not in worktree_name or worktree_name.endswith("-plan") is False


def test_implement_from_plan_file_fails_when_not_found() -> None:
    """Test that command fails when plan file doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(implement, ["nonexistent-plan.md"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_from_plan_file_dry_run() -> None:
    """Test dry-run mode for plan file implementation."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert str(plan_file) in result.output
        assert len(git.added_worktrees) == 0
        # Verify plan file NOT deleted in dry-run
        assert plan_file.exists()


# Branch Conflict Tests


def test_implement_fails_when_branch_exists_issue_mode() -> None:
    """Test that issue mode fails when branch already exists."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--worktree-name", "existing-branch"], obj=ctx)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "already exists" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_fails_when_branch_exists_file_mode() -> None:
    """Test that file mode fails when branch already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan", encoding="utf-8")

        result = runner.invoke(
            implement, [str(plan_file), "--worktree-name", "existing-branch"], obj=ctx
        )

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "already exists" in result.output
        assert len(git.added_worktrees) == 0


# Submit Flag Tests


def test_implement_with_submit_flag_from_issue() -> None:
    """Test --submit flag from issue includes command chain in manual instructions."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify manual instructions show all three commands
        assert "/erk:implement-plan" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:submit-squashed-branch" in result.output

        # Verify script flag hint shows --submit
        assert "--submit --script" in result.output


def test_implement_with_submit_flag_from_file() -> None:
    """Test implementing from file with --submit flag includes command chain."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Feature Plan\n\nImplement feature.", encoding="utf-8")

        result = runner.invoke(implement, [str(plan_file), "--submit"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify manual instructions show all three commands
        assert "/erk:implement-plan" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:submit-squashed-branch" in result.output

        # Verify plan file was deleted (moved to worktree)
        assert not plan_file.exists()


def test_implement_without_submit_uses_default_command() -> None:
    """Test that default behavior (without --submit) still works unchanged."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree" in result.output

        # Verify manual instructions show only implement-plan
        assert "/erk:implement-plan" in result.output
        assert "/fast-ci" not in result.output
        assert "/gt:submit-squashed-branch" not in result.output

        # Verify script flag hint doesn't show --submit
        assert "--submit" not in result.output or "--submit --script" not in result.output


def test_implement_submit_in_script_mode() -> None:
    """Test that --script --submit combination generates correct activation script."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--submit", "--script"], obj=ctx)

        assert result.exit_code == 0

        # Verify script path is output
        assert result.stdout
        script_path = Path(result.stdout.strip())

        # Verify script file exists and read its content
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")

        # Verify script content contains chained commands
        assert "/erk:implement-plan" in script_content
        assert "/fast-ci" in script_content
        assert "/gt:submit-squashed-branch" in script_content

        # Verify commands are chained with &&
        assert "&&" in script_content


def test_implement_submit_with_dry_run() -> None:
    """Test that --submit --dry-run shows all commands that would be executed."""
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        result = runner.invoke(implement, ["#42", "--submit", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

        # Verify all three commands shown in dry-run output
        assert "/erk:implement-plan" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:submit-squashed-branch" in result.output

        # Verify no worktree was actually created
        assert len(git.added_worktrees) == 0
