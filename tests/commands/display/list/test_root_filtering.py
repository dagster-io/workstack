"""Tests for root worktree stack filtering behavior.

These tests verify that root worktree shows only ancestors + current branch,
while other worktrees show full context with checked-out descendants.

## Bug History

Before the fix (commit XXXX), the code had special handling for "trunk" branches
that would show descendants if they had worktrees. This caused incorrect behavior:

    root [main]
      ◯  feature-b    <- WRONG: showed descendant with worktree
      ◉  main

The fix replaced `is_trunk` logic with `is_root_worktree` logic, which correctly
shows only ancestors + current for the root worktree:

    root [main]
      ◉  main         <- CORRECT: only trunk shown

These tests would have failed with the old implementation, catching the regression.
"""

from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_root_on_trunk_shows_only_trunk() -> None:
    """Root worktree on trunk branch shows only the trunk itself (no descendants).

    Setup:
        - Stack: main → feature-a → feature-b
        - Root on main (trunk)
        - Worktree on feature-b

    Before fix:
        root [main]
          ◯  feature-b    <- WRONG: showed descendant with worktree
          ◉  main

    After fix:
        root [main]
          ◉  main         <- CORRECT: only trunk shown
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create feature-b worktree
        env.create_linked_worktree("feature-b", "feature-b", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-a"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-a": BranchMetadata(
                    name="feature-a",
                    parent="main",
                    children=["feature-b"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-b": BranchMetadata(
                    name="feature-b",
                    parent="feature-a",
                    children=[],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find root and feature-b sections
        root_section_start = None
        feature_b_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("feature-b"):
                feature_b_section_start = i

        assert root_section_start is not None
        assert feature_b_section_start is not None

        # Get root section (from root header to feature-b header)
        root_section = lines[root_section_start:feature_b_section_start]
        root_section_text = "\n".join(root_section)

        # Root should show ONLY main (no descendants, even with worktrees)
        assert "◉  main" in root_section_text, "Root should show main"
        assert "feature-a" not in root_section_text, (
            f"Root should NOT show feature-a (descendant). Root section:\n{root_section_text}"
        )
        assert "feature-b" not in root_section_text, (
            "Root should NOT show feature-b even though it has a worktree. "
            f"Root section:\n{root_section_text}"
        )


def test_root_on_non_trunk_shows_ancestors_only() -> None:
    """Root worktree on non-trunk branch shows ancestors + current (no descendants).

    Setup:
        - Stack: main → feature-a → feature-b → feature-c
        - Root on feature-b
        - Worktree on feature-c

    Expected:
        root [feature-b]
          ◉  feature-b       <- current
          ◯  feature-a       <- ancestor
          ◯  main            <- ancestor
                             <- feature-c NOT shown (descendant)

        feature-c [feature-c]
          ◉  feature-c
          ◯  feature-b
          ◯  feature-a
          ◯  main
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create feature-c worktree
        env.create_linked_worktree("feature-c", "feature-c", chdir=False)

        # Build ops from branches - root is on feature-b (non-trunk)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-a"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-a": BranchMetadata(
                    name="feature-a",
                    parent="main",
                    children=["feature-b"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-b": BranchMetadata(
                    name="feature-b",
                    parent="feature-a",
                    children=["feature-c"],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
                "feature-c": BranchMetadata(
                    name="feature-c",
                    parent="feature-b",
                    children=[],
                    is_trunk=False,
                    commit_sha="jkl012",
                ),
            },
            current_branch="feature-b",  # Root on feature-b
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find root and feature-c sections
        root_section_start = None
        feature_c_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("feature-c"):
                feature_c_section_start = i

        assert root_section_start is not None
        assert feature_c_section_start is not None

        # Get root section (from root header to feature-c header)
        root_section = lines[root_section_start:feature_c_section_start]
        root_section_text = "\n".join(root_section)

        # Root should show: feature-b (current), feature-a (ancestor), main (ancestor)
        # But NOT feature-c (descendant)
        assert "◉  feature-b" in root_section_text, "Root should show feature-b (current)"
        assert "◯  feature-a" in root_section_text, "Root should show feature-a (ancestor)"
        assert "◯  main" in root_section_text, "Root should show main (ancestor)"
        assert "feature-c" not in root_section_text, (
            f"Root should NOT show feature-c (descendant). Root section:\n{root_section_text}"
        )

        # Get feature-c section (from feature-c header to end)
        feature_c_section = lines[feature_c_section_start:]
        feature_c_section_text = "\n".join(feature_c_section)

        # Feature-c worktree should show full stack (all ancestors)
        assert "◉  feature-c" in feature_c_section_text
        assert "◯  feature-b" in feature_c_section_text
        assert "◯  feature-a" in feature_c_section_text
        assert "◯  main" in feature_c_section_text


def test_non_root_worktree_shows_descendants_with_worktrees() -> None:
    """Non-root worktrees show descendants that are checked out somewhere.

    Setup:
        - Stack: main → feature-a → feature-b → feature-c
        - Root on main
        - Worktree-a on feature-a
        - Worktree-c on feature-c

    Expected:
        root [main]
          ◉  main            <- only main (no descendants for root)

        worktree-a [feature-a]
          ◉  feature-a       <- current
          ◯  main            <- ancestor
          ◯  feature-c       <- descendant with worktree (skips feature-b)
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktrees
        env.create_linked_worktree("worktree-a", "feature-a", chdir=False)
        env.create_linked_worktree("worktree-c", "feature-c", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-a"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-a": BranchMetadata(
                    name="feature-a",
                    parent="main",
                    children=["feature-b"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-b": BranchMetadata(
                    name="feature-b",
                    parent="feature-a",
                    children=["feature-c"],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
                "feature-c": BranchMetadata(
                    name="feature-c",
                    parent="feature-b",
                    children=[],
                    is_trunk=False,
                    commit_sha="jkl012",
                ),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find sections
        root_section_start = None
        worktree_a_section_start = None
        worktree_c_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("worktree-a"):
                worktree_a_section_start = i
            if line.startswith("worktree-c"):
                worktree_c_section_start = i

        assert root_section_start is not None
        assert worktree_a_section_start is not None
        assert worktree_c_section_start is not None

        # Get root section
        root_section = lines[root_section_start:worktree_a_section_start]
        root_section_text = "\n".join(root_section)

        # Root should show only main
        assert "◉  main" in root_section_text
        assert "feature-a" not in root_section_text
        assert "feature-c" not in root_section_text

        # Get worktree-a section
        worktree_a_section = lines[worktree_a_section_start:worktree_c_section_start]
        worktree_a_section_text = "\n".join(worktree_a_section)

        # Worktree-a should show: feature-a (current), main (ancestor), feature-c (descendant)
        # But NOT feature-b (no worktree)
        assert "◉  feature-a" in worktree_a_section_text
        assert "◯  main" in worktree_a_section_text
        assert "◯  feature-c" in worktree_a_section_text, (
            "worktree-a should show feature-c (descendant with worktree). "
            f"Section:\n{worktree_a_section_text}"
        )
        assert "feature-b" not in worktree_a_section_text, (
            "worktree-a should NOT show feature-b (no worktree). "
            f"Section:\n{worktree_a_section_text}"
        )
