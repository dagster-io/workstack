from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_list_outputs_names_not_paths() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees
        env.create_linked_worktree(name="foo", branch="foo", chdir=False)
        env.create_linked_worktree(name="bar", branch="feature/bar", chdir=False)

        # Build ops
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(sha="abc123"),
                "foo": BranchMetadata.branch("foo", sha="def456"),
                "feature/bar": BranchMetadata.branch("feature/bar", sha="ghi789"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier comparison
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # First line should be root with branch (paths are not shown in list output)
        assert lines[0].startswith("root")
        # Note: List command does not show paths, only names and branches

        # Remaining lines should be worktrees, sorted by name
        # Worktrees show name, branch (or = if same), PR info, and plan status
        worktree_lines = sorted(lines[1:])
        # Check that worktrees are listed by name
        assert any("bar" in line and "feature/bar" in line for line in worktree_lines)
        assert any("foo" in line for line in worktree_lines)
