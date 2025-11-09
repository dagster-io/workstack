from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.commands.graphite.test_land_stack import simulated_workstack_env
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
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

        # First line should be root with branch and path
        assert lines[0].startswith("root")
        assert str(env.root_worktree) in lines[0]

        # Remaining lines should be worktrees, sorted by name
        worktree_lines = sorted(lines[1:])
        workstacks_dir = env.workstacks_root / "repo"
        assert worktree_lines == [
            f"bar  (feature/bar) [{workstacks_dir / 'bar'}]",
            f"foo  (=)           [{workstacks_dir / 'foo'}]",
        ]
