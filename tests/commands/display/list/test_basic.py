from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.gitops import WorktreeInfo


def test_list_outputs_names_not_paths() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktrees in the location determined by global config
        repo_name = env.cwd.name
        workstacks_dir = env.workstacks_root / repo_name
        (workstacks_dir / "foo").mkdir(parents=True)
        (workstacks_dir / "bar").mkdir(parents=True)

        # Build fake git ops with worktree info
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "foo", branch="foo"),
                    WorktreeInfo(path=workstacks_dir / "bar", branch="feature/bar"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier comparison
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # First line should be root with branch, PR placeholder, and plan placeholder
        assert lines[0].startswith("root")
        assert "(main)" in lines[0]
        assert "[no PR]" in lines[0]
        assert "[no plan]" in lines[0]

        # Remaining lines should be worktrees with PR/plan info, sorted by name
        worktree_lines = sorted(lines[1:])
        # Each line should contain: name (branch) [no PR] [no plan]
        assert len(worktree_lines) == 2
        assert worktree_lines[0].startswith("bar")
        assert "(feature/bar)" in worktree_lines[0]
        assert "[no PR]" in worktree_lines[0]
        assert "[no plan]" in worktree_lines[0]

        assert worktree_lines[1].startswith("foo")
        assert "(=)" in worktree_lines[1]  # foo == foo, so displayed as "="
        assert "[no PR]" in worktree_lines[1]
        assert "[no plan]" in worktree_lines[1]
