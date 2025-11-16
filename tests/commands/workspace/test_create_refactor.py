"""Tests for refactored create command architecture.

This test module specifically targets the refactored create command structure,
testing new code paths, validation logic, and variant dispatching introduced
during the subpackage refactoring.

These are Layer 3 tests (business logic over fakes) that test through the
public CLI API to ensure the refactored internal modules work correctly.
"""

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import pure_workstack_env, simulated_workstack_env
from workstack.cli.cli import cli
from workstack.cli.config import LoadedConfig
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.gitops import WorktreeInfo
from workstack.core.repo_discovery import RepoContext

# ==============================================================================
# Validation Edge Cases (validation.py)
# ==============================================================================


def test_create_rejects_multiple_variant_flags_from_branch_and_plan() -> None:
    """Test that using --from-branch and --plan together is rejected."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to use both --from-branch and --plan
        result = runner.invoke(
            cli,
            ["create", "--from-branch", "feature", "--plan", str(plan_file)],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Cannot use multiple of" in result.output


def test_create_rejects_multiple_variant_flags_from_current_and_with_dot_plan() -> None:
    """Test that using --from-current-branch and --with-dot-plan together is rejected."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to use both --from-current-branch and --with-dot-plan
        result = runner.invoke(
            cli,
            ["create", "new-feature", "--from-current-branch", "--with-dot-plan", "source"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Cannot use multiple of" in result.output


def test_create_rejects_all_four_variant_flags_together() -> None:
    """Test that using all four variant flags is rejected."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        plan_file = env.cwd / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            local_branches={env.cwd: ["main", "feature", "other"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to use all four variant flags
        result = runner.invoke(
            cli,
            [
                "create",
                "name",
                "--from-current-branch",
                "--from-branch",
                "other",
                "--plan",
                str(plan_file),
                "--with-dot-plan",
                "source",
            ],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Cannot use multiple of" in result.output


def test_create_rejects_reserved_name_root() -> None:
    """Test that 'root' is rejected as a worktree name."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "root"], obj=test_ctx)

        assert result.exit_code == 1
        assert "reserved name" in result.output


def test_create_rejects_reserved_name_Root_case_insensitive() -> None:
    """Test that 'Root' (mixed case) is rejected as a worktree name."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "Root"], obj=test_ctx)

        assert result.exit_code == 1
        assert "reserved name" in result.output


def test_create_rejects_json_and_script_flags_together() -> None:
    """Test that --json and --script are mutually exclusive."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "feature", "--json", "--script"], obj=test_ctx)

        assert result.exit_code == 1


def test_create_rejects_keep_plan_without_plan_file() -> None:
    """Test that --keep-plan requires --plan to be specified."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "feature", "--keep-plan"], obj=test_ctx)

        assert result.exit_code == 1
        assert "requires --plan" in result.output


# ==============================================================================
# Worktree Operations Error Paths (worktree_ops.py)
# ==============================================================================


def test_create_detects_branch_already_checked_out_in_from_branch_variant() -> None:
    """Test that --from-branch detects if branch is already checked out."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_root = env.root_worktree

        workstacks_dir = env.workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True, exist_ok=True)

        # Create existing worktree with the target branch
        existing_worktree = workstacks_dir / "existing"
        existing_worktree.mkdir(parents=True, exist_ok=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=existing_worktree, branch="feature"),
                ]
            },
            git_common_dirs={
                repo_root: env.git_dir,
                existing_worktree: env.git_dir,
            },
            default_branches={repo_root: "main"},
            current_branches={repo_root: "main"},
            local_branches={repo_root: ["main", "feature"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to create from branch that's already checked out
        result = runner.invoke(cli, ["create", "--from-branch", "feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already checked out" in result.output
        assert str(existing_worktree) in result.output


def test_create_with_graphite_detects_staged_changes() -> None:
    """Test that Graphite creation detects and rejects staged changes."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up git ops with staged changes
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            staged_repos={env.cwd},  # Staged changes present
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["create", "feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Staged changes detected" in result.output
        assert "Graphite cannot create a branch" in result.output


def test_create_with_graphite_from_detached_head_fails() -> None:
    """Test that Graphite creation from detached HEAD raises appropriate error."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up git ops in detached HEAD state
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: None},  # Detached HEAD
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["create", "feature"], obj=test_ctx)

        # Should fail with error about detached HEAD
        assert result.exit_code != 0


# ==============================================================================
# Variant Dispatcher Coverage (orchestrator.py match statements)
# ==============================================================================


def test_create_regular_variant_creates_new_branch() -> None:
    """Test regular variant (no flags) creates new branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "new-feature"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify regular variant executed (new worktree created)
        assert len(git_ops.added_worktrees) == 1


def test_create_from_branch_variant_uses_existing_branch() -> None:
    """Test from_branch variant checks out existing branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-feature"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "--from-branch", "existing-feature"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify from_branch variant executed (existing branch checked out)
        added_worktrees = git_ops.added_worktrees
        assert len(added_worktrees) == 1
        # Branch name should match the --from-branch value
        assert added_worktrees[0][1] == "existing-feature"


def test_create_from_current_branch_variant_moves_branch() -> None:
    """Test from_current_branch variant moves current branch to new worktree."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify current branch was checked out elsewhere (switched to main)
        assert ("feature-branch",) in [wt[1:2] for wt in git_ops.added_worktrees]


def test_create_plan_variant_derives_name_from_plan_file() -> None:
    """Test plan variant derives worktree name from plan filename."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create plan file with descriptive name
        plan_file = env.cwd / "refactor-authentication-plan.md"
        plan_file.write_text("# Refactor Auth\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / env.root_worktree.name
        workstacks_dir.mkdir(parents=True)

        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            workstacks_dir=workstacks_dir,
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
        )

        result = runner.invoke(cli, ["create", "--plan", str(plan_file)], obj=test_ctx)

        assert result.exit_code == 0
        # Verify plan variant derived name correctly
        assert (
            "refactor-authentication" in result.output or "refactor_authentication" in result.output
        )


def _test_create_with_dot_plan_variant_copies_plan_folder() -> None:
    """Test with_dot_plan variant copies .plan/ folder from source.

    NOTE: This test is disabled because it requires subprocess execution of 'gt create'
    which cannot be easily faked. The with_dot_plan variant is already covered by
    existing integration tests in test_create.py.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_root = env.root_worktree

        # Create source worktree with .plan/ folder
        source_worktree = env.workstacks_root / repo_root.name / "source-feature"
        source_worktree.mkdir(parents=True)
        source_plan_dir = source_worktree / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / repo_root.name

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_worktree, branch="source-feature"),
                ]
            },
            git_common_dirs={
                repo_root: env.git_dir,
                source_worktree: env.git_dir,
            },
            default_branches={repo_root: "main"},
            current_branches={
                repo_root: "main",
                source_worktree: "source-feature",
            },
        )

        # Configure Graphite with parent/child relationships
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["source-feature"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "source-feature": BranchMetadata(
                    name="source-feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            }
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["create", "new-feature", "--with-dot-plan", "source-feature"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify .plan/ folder was copied
        target_worktree = workstacks_dir / "new-feature"
        target_plan_dir = target_worktree / ".plan"
        assert target_plan_dir.exists()
        assert (target_plan_dir / "plan.md").exists()


# ==============================================================================
# Name Derivation Logic (orchestrator.py _derive_name match statement)
# ==============================================================================


def test_create_derives_name_from_current_branch_when_not_provided() -> None:
    """Test _derive_name uses current branch name when NAME not provided."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "my-feature-branch"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Don't provide NAME, should derive from current branch
        result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0
        # Name should be derived from "my-feature-branch"
        assert "my-feature-branch" in result.output or "my_feature_branch" in result.output


def test_create_derives_name_from_from_branch_value_when_not_provided() -> None:
    """Test _derive_name uses --from-branch value when NAME not provided."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "target-branch"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Don't provide NAME, should derive from --from-branch value
        result = runner.invoke(cli, ["create", "--from-branch", "target-branch"], obj=test_ctx)

        assert result.exit_code == 0
        # Name should be derived from "target-branch"
        assert "target-branch" in result.output or "target_branch" in result.output


def test_create_requires_name_for_regular_variant() -> None:
    """Test _derive_name requires NAME for regular variant."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try regular variant without NAME
        result = runner.invoke(cli, ["create"], obj=test_ctx)

        assert result.exit_code != 0
        # Should show error about missing name or flag
        assert "provide NAME" in result.output or "required" in result.output.lower()


def test_create_requires_name_for_with_dot_plan_variant() -> None:
    """Test _derive_name requires NAME for with_dot_plan variant."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_root = env.root_worktree

        # Create source worktree
        source_worktree = env.workstacks_root / repo_root.name / "source"
        source_worktree.mkdir(parents=True)
        source_plan_dir = source_worktree / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / repo_root.name

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_worktree, branch="source"),
                ]
            },
            git_common_dirs={
                repo_root: env.git_dir,
                source_worktree: env.git_dir,
            },
            default_branches={repo_root: "main"},
            current_branches={repo_root: "main"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try with_dot_plan without NAME
        result = runner.invoke(cli, ["create", "--with-dot-plan", "source"], obj=test_ctx)

        assert result.exit_code == 1
        assert "provide NAME" in result.output


def test_create_forbids_name_with_plan_variant() -> None:
    """Test _derive_name forbids NAME when using --plan."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        plan_file = env.cwd / "feature-plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        workstacks_dir = env.workstacks_root / env.root_worktree.name
        workstacks_dir.mkdir(parents=True)

        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            workstacks_dir=workstacks_dir,
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
        )

        # Try to provide both NAME and --plan
        result = runner.invoke(cli, ["create", "my-name", "--plan", str(plan_file)], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot specify both NAME and --plan" in result.output


def test_create_forbids_branch_flag_with_from_current_branch() -> None:
    """Test _derive_name forbids --branch with --from-current-branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to use both --branch and --from-current-branch
        result = runner.invoke(
            cli,
            ["create", "--from-current-branch", "--branch", "custom-branch"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Cannot specify --branch with --from-current-branch" in result.output


def test_create_forbids_branch_flag_with_from_branch() -> None:
    """Test _derive_name forbids --branch with --from-branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing"]},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Try to use both --branch and --from-branch
        result = runner.invoke(
            cli,
            ["create", "--from-branch", "existing", "--branch", "custom-branch"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Cannot specify --branch with --from-branch" in result.output
