"""Tests for workstack create command output behavior."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import pure_workstack_env, simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.gitops import WorktreeInfo


def test_create_from_current_branch_outputs_script_path_to_stdout() -> None:
    """Test that create --from-current-branch outputs script path to stdout, not stderr.

    This test verifies that the shell integration handler can read the script path
    from stdout. If the script path is written to stderr, the handler will miss it
    and display 'no directory change needed' instead of switching to the new worktree.

    See: https://github.com/anthropics/workstack/issues/XXX
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

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
        expected_worktree_path = workstacks_dir / "my-feature"
        assert str(expected_worktree_path) in script_content, (
            f"Script should cd to {expected_worktree_path}"
        )


@pytest.mark.skip(
    reason="Requires real git/graphite subprocess execution; error validation tested separately"
)
def test_create_with_dot_plan_explicit_source() -> None:
    """Test --with-dot-plan with explicit source workstack argument."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Set up Graphite metadata: source-wt branch has parent "main"
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["source-branch"], commit_sha="abc123"
                ),
                "source-branch": BranchMetadata(
                    name="source-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            }
        )

        # Create source worktree with .plan/ folder
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)
        source_plan_dir = source_wt / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("# Test Plan\nSome plan content", encoding="utf-8")
        (source_plan_dir / "progress.md").write_text("- [ ] Step 1\n- [ ] Step 2", encoding="utf-8")

        # Set up git state
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="source-branch"),
                ]
            },
            current_branches={env.cwd: "main", source_wt: "source-branch"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={
                env.workstacks_root,
                env.repo.workstacks_dir,
                source_wt,
                source_plan_dir,
            },
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        # Act: Create new worktree with --with-dot-plan
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "source-wt"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"Output: {result.output}")
        assert result.exit_code == 0

        # Assert: .plan/ folder was copied
        new_wt = env.repo.workstacks_dir / "new-wt"
        new_plan_dir = new_wt / ".plan"
        assert new_plan_dir.exists()
        assert (new_plan_dir / "plan.md").exists()
        assert (new_plan_dir / "progress.md").exists()

        # Assert: Plan content matches source
        assert (new_plan_dir / "plan.md").read_text(
            encoding="utf-8"
        ) == "# Test Plan\nSome plan content"


@pytest.mark.skip(
    reason="Requires real git/graphite subprocess execution; error validation tested separately"
)
def test_create_with_dot_plan_implicit_source() -> None:
    """Test --with-dot-plan without argument (uses current workstack)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Set up Graphite metadata
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["source-branch"], commit_sha="abc123"
                ),
                "source-branch": BranchMetadata(
                    name="source-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            }
        )

        # Create source worktree with .plan/ folder
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)
        source_plan_dir = source_wt / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("# Plan Content", encoding="utf-8")

        # Set up git state - current directory is inside source-wt
        source_subdir = source_wt / "subdir"
        source_subdir.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="source-branch"),
                ]
            },
            current_branches={source_subdir: "source-branch", source_wt: "source-branch"},
            default_branches={env.cwd: "main"},
            git_common_dirs={source_subdir: env.git_dir},
            existing_paths={
                env.workstacks_root,
                source_wt,
                source_plan_dir,
            },
        )

        # Override cwd to be inside source worktree
        test_ctx = env.build_context(
            git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True, cwd=source_subdir
        )

        # Act: Create new worktree with --with-dot-plan (no argument)
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"Output: {result.output}")
        assert result.exit_code == 0

        # Assert: .plan/ folder was copied
        new_plan_dir = env.repo.workstacks_dir / "new-wt" / ".plan"
        assert new_plan_dir.exists()


def test_create_with_dot_plan_graphite_disabled() -> None:
    """Test --with-dot-plan fails when Graphite is disabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create source worktree with .plan/
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)
        (source_wt / ".plan").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={source_wt},
        )

        # Graphite disabled
        test_ctx = env.build_context(git_ops=git_ops, use_graphite=False)

        # Act: Try to create with --with-dot-plan
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "source-wt"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed with error about Graphite requirement
        assert result.exit_code == 1
        assert "--with-dot-plan requires Graphite" in result.output


@pytest.mark.skip(
    reason="Requires real git/graphite subprocess execution; error validation tested separately"
)
def test_create_with_dot_plan_source_not_found() -> None:
    """Test --with-dot-plan fails when source workstack doesn't exist."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.workstacks_root},
        )

        test_ctx = env.build_context(git_ops=git_ops, use_graphite=True)

        # Act: Try to create with non-existent source
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "nonexistent"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Error message about source not found
        assert result.exit_code == 1
        assert "Source workstack 'nonexistent' not found" in result.output


def test_create_with_dot_plan_no_plan_folder() -> None:
    """Test --with-dot-plan fails when source has no .plan/ folder."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create source worktree WITHOUT .plan/ folder
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={
                env.workstacks_root,
                source_wt,
            },
        )

        test_ctx = env.build_context(git_ops=git_ops, use_graphite=True)

        # Act: Try to create with source that has no plan
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "source-wt"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Error about missing .plan/ folder
        assert result.exit_code == 1
        assert "has no .plan/ folder" in result.output


def test_create_with_dot_plan_no_parent_branch() -> None:
    """Test --with-dot-plan fails when source branch has no Graphite parent."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Set up Graphite without parent for source branch
        graphite_ops = FakeGraphiteOps(
            branches={}  # Empty - source-branch not tracked
        )

        # Create source worktree with .plan/
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)
        source_plan_dir = source_wt / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("content", encoding="utf-8")

        git_ops = FakeGitOps(
            current_branches={source_wt: "source-branch"},
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={
                env.workstacks_root,
                env.repo.workstacks_dir,
                source_wt,
                source_plan_dir,
            },
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        # Act: Try to create when source has no parent
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "source-wt"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Error about no parent branch
        assert result.exit_code == 1
        assert "has no parent in Graphite" in result.output


@pytest.mark.skip(
    reason="Requires real git/graphite subprocess execution; error validation tested separately"
)
def test_create_with_dot_plan_copies_all_files() -> None:
    """Test that both plan.md and progress.md are copied."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Set up Graphite metadata
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["source-branch"], commit_sha="abc123"
                ),
                "source-branch": BranchMetadata(
                    name="source-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            }
        )

        # Create source with both files
        source_wt = env.repo.workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)
        source_plan_dir = source_wt / ".plan"
        source_plan_dir.mkdir()
        (source_plan_dir / "plan.md").write_text("plan content", encoding="utf-8")
        (source_plan_dir / "progress.md").write_text("progress content", encoding="utf-8")

        git_ops = FakeGitOps(
            current_branches={source_wt: "source-branch"},
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={
                env.workstacks_root,
                env.repo.workstacks_dir,
                source_wt,
                source_plan_dir,
            },
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        # Act: Create with --with-dot-plan
        result = runner.invoke(
            cli,
            ["create", "new-wt", "--with-dot-plan", "source-wt"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Both files exist in new worktree
        assert result.exit_code == 0
        new_plan_dir = env.repo.workstacks_dir / "new-wt" / ".plan"
        assert (new_plan_dir / "plan.md").exists()
        assert (new_plan_dir / "progress.md").exists()
        assert (new_plan_dir / "plan.md").read_text(encoding="utf-8") == "plan content"
        assert (new_plan_dir / "progress.md").read_text(encoding="utf-8") == "progress content"
