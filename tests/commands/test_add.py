"""Tests for erk create command output behavior."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.git.abc import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_add_from_current_branch_outputs_script_path_to_stdout() -> None:
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
            ["add", "--from-current-branch", "--script"],
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
