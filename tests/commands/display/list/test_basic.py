from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from erk.core.graphite.fake import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi


def test_list_outputs_names_not_paths() -> None:
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create worktrees in the location determined by global config
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        # Build fake git ops with worktree info
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=repo_dir / "foo", branch="foo"),
                    WorktreeInfo(path=repo_dir / "bar", branch="feature/bar"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),
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
