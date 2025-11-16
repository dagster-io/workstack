from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.gitops import WorktreeInfo
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import pure_workstack_env
from tests.test_utils.output_helpers import strip_ansi


def test_list_outputs_names_not_paths() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create worktrees in the location determined by global config
        repo_name = env.cwd.name
        workstacks_dir = env.workstacks_root / repo_name

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
            graphite_ops=FakeGraphiteOps(pr_info={}),
            show_pr_info=False,  # Don't require PR info for this test
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier comparison
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # First line should be "## Worktrees" header
        assert lines[0] == "## Worktrees"

        # Skip empty line after header (line 1)
        # Line 2 should be root with branch, PR placeholder, and plan placeholder
        assert lines[2].startswith("root")
        assert "(main)" in lines[2]
        assert "[no PR]" in lines[2]
        assert "[no plan]" in lines[2]

        # Remaining worktree lines should show PR/plan info, sorted by name
        worktree_lines = sorted(lines[3:])
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
