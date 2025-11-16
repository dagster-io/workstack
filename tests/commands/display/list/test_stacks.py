import json

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env, simulated_workstack_env
from tests.test_utils.output_helpers import strip_ansi
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.gitops import WorktreeInfo
from workstack.core.graphite_ops import RealGraphiteOps


def test_list_with_stacks_flag() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata for graphite stack
        # Linear stack: main → ts-phase-1 → ts-phase-2 → ts-phase-3
        # Plus sibling branch (should NOT be shown in ts worktree stack)
        branches = {
            "main": BranchMetadata.trunk(
                "main", children=["schrockn/ts-phase-1", "sibling-branch"]
            ),
            "schrockn/ts-phase-1": BranchMetadata.branch(
                "schrockn/ts-phase-1", "main", children=["schrockn/ts-phase-2"]
            ),
            "schrockn/ts-phase-2": BranchMetadata.branch(
                "schrockn/ts-phase-2", "schrockn/ts-phase-1", children=["schrockn/ts-phase-3"]
            ),
            "schrockn/ts-phase-3": BranchMetadata.branch(
                "schrockn/ts-phase-3", "schrockn/ts-phase-2", children=[]
            ),
            "sibling-branch": BranchMetadata.branch("sibling-branch", "main", children=[]),
        }

        # Create worktrees in pure mode
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Build fake git ops
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "ts", branch="schrockn/ts-phase-2"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                workstacks_dir / "ts": env.git_dir,
            },
            current_branches={
                env.cwd: "main",
                workstacks_dir / "ts": "schrockn/ts-phase-2",
            },
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find the root section and ts section
        root_section_start = None
        ts_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("ts"):
                ts_section_start = i

        assert root_section_start is not None
        assert ts_section_start is not None

        # Get the ts section (from ts header to end)
        ts_section = lines[ts_section_start:]
        ts_section_text = "\n".join(ts_section)

        # Check ts worktree stack shows linear chain in reversed order
        # (descendants at top, trunk at bottom)
        # Note: ts-phase-3 is NOT shown because it has no worktree
        assert lines[ts_section_start].startswith("ts")
        assert "◉  schrockn/ts-phase-2" in ts_section_text
        assert "◯  schrockn/ts-phase-1" in ts_section_text
        assert "◯  main" in ts_section_text

        # ts-phase-3 should NOT appear (no worktree for it)
        assert "schrockn/ts-phase-3" not in ts_section_text

        # Verify sibling branch is NOT shown (regression test)
        assert "sibling-branch" not in output

        # Verify order within ts section: phase-2 before phase-1, phase-1 before main
        # Use the marked versions to avoid matching the header
        phase_2_idx = ts_section_text.index("◉  schrockn/ts-phase-2")
        phase_1_idx = ts_section_text.index("◯  schrockn/ts-phase-1")
        main_in_stack_idx = ts_section_text.index("◯  main")

        assert phase_2_idx < phase_1_idx < main_in_stack_idx


def test_list_with_stacks_graphite_disabled() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build fake git ops
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 1
        assert "Error: --stacks requires graphite to be enabled" in result.output


def test_list_with_stacks_no_graphite_cache() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # No graphite cache (testing graceful degradation with empty branches)

        # Build fake git ops
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches={}, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        # Should succeed but not show stack info (graceful degradation)
        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output
        output = strip_ansi(result.output)
        # Should show worktree but no stack visualization
        assert output.startswith("root")
        # Should not have any circle markers
        assert "◉" not in output
        assert "◯" not in output


def test_list_with_stacks_highlights_current_branch_not_worktree_branch() -> None:
    """
    Regression test for bug where the worktree's checkout branch was highlighted
    instead of the current working directory's checked-out branch.

    When running `workstack ls --stacks` from a worktree that has switched branches
    (e.g., temporal-stack worktree is on ts-phase-4, but current directory is on ts-phase-3),
    the highlighted marker (◉) should show ts-phase-3, not ts-phase-4.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata for graphite stack
        branches = {
            "main": BranchMetadata.trunk("main", children=["schrockn/ts-phase-1"]),
            "schrockn/ts-phase-1": BranchMetadata.branch(
                "schrockn/ts-phase-1", "main", children=["schrockn/ts-phase-2"]
            ),
            "schrockn/ts-phase-2": BranchMetadata.branch(
                "schrockn/ts-phase-2", "schrockn/ts-phase-1", children=["schrockn/ts-phase-3"]
            ),
            "schrockn/ts-phase-3": BranchMetadata.branch(
                "schrockn/ts-phase-3", "schrockn/ts-phase-2", children=["schrockn/ts-phase-4"]
            ),
            "schrockn/ts-phase-4": BranchMetadata.branch(
                "schrockn/ts-phase-4", "schrockn/ts-phase-3", children=[]
            ),
        }

        # Create worktree
        workstacks_dir = env.workstacks_root / env.cwd.name
        temporal_stack_dir = workstacks_dir / "temporal-stack"

        # Build fake git ops
        # Key setup: The worktree is registered with ts-phase-4,
        # but currently checked out to ts-phase-3
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=temporal_stack_dir, branch="schrockn/ts-phase-4"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                temporal_stack_dir: env.git_dir,
            },
            current_branches={
                env.cwd: "main",
                temporal_stack_dir: "schrockn/ts-phase-3",  # Actually on phase-3
            },
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)

        # The stack visualization should highlight ts-phase-3 (actual current branch)
        # NOT ts-phase-4 (the worktree's registered branch from git worktree list)
        lines = output.splitlines()

        # Find the stack visualization lines
        phase_3_line = None
        phase_4_line = None
        for line in lines:
            if "schrockn/ts-phase-3" in line and line.strip().startswith("◉"):
                phase_3_line = line
            if "schrockn/ts-phase-4" in line and line.strip().startswith("◉"):
                phase_4_line = line

        # FIXED: ts-phase-3 should be highlighted because that's the actual checked-out branch
        assert phase_3_line is not None, (
            "Expected ts-phase-3 to be highlighted with ◉, "
            f"but it wasn't found in output:\n{output}"
        )

        # ts-phase-4 should NOT be highlighted
        assert phase_4_line is None, (
            "ts-phase-4 should NOT be highlighted with ◉ "
            "because it's only the registered branch, not the actual checked-out branch. "
            f"Output:\n{output}"
        )


def test_list_with_stacks_root_repo_does_not_duplicate_branch() -> None:
    """
    Regression test: Root repo should be displayed as "root", not the branch name.

    For example, if on "master" branch with stack [foo, master]:
    WRONG:
        master [master]
          ◯  foo
          ◉  master   <- duplicate!

    CORRECT:
        root [master]
          ◯  foo
          ◉  master
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata with master as parent of foo
        branches = {
            "master": BranchMetadata.trunk("master", children=["foo"]),
            "foo": BranchMetadata.branch("foo", "master", children=[]),
        }

        # Build fake git ops - only root repo on master
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="master")]},
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Should have header line with "root" as the name
        assert lines[0].startswith("root")

        # Only master should be shown (foo has no worktree)
        assert "◉  master" in output
        assert "foo" not in output, (
            f"foo should be hidden because it has no worktree. Output:\n{output}"
        )


def test_list_with_stacks_shows_descendants_with_worktrees() -> None:
    """
    Non-root worktrees should show descendants with worktrees.
    Root worktree shows only current branch (no descendants).

    When root is on master with stack [master, foo] and there's a foo worktree:

    EXPECTED:
        root [master]
          ◉  master     <- only current branch (root shows no descendants)

        foo [foo]
          ◉  foo
          ◯  master
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata with master as parent of foo
        branches = {
            "master": BranchMetadata.trunk("master", children=["foo"]),
            "foo": BranchMetadata.branch("foo", "master", children=[]),
        }

        # Create foo worktree
        workstacks_dir = env.workstacks_root / env.cwd.name
        foo_worktree_dir = workstacks_dir / "foo"

        # Build fake git ops - root on master, foo worktree on foo branch
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="master"),
                    WorktreeInfo(path=foo_worktree_dir, branch="foo"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                foo_worktree_dir: env.git_dir,
            },
            current_branches={
                env.cwd: "master",
                foo_worktree_dir: "foo",
            },
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find the root section and foo section
        root_section_start = None
        foo_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("foo"):
                foo_section_start = i

        assert root_section_start is not None, "Should have root section"
        assert foo_section_start is not None, "Should have foo worktree section"

        # Get root section lines (from root header to foo header)
        root_section = lines[root_section_start:foo_section_start]

        # Root section should show ONLY master (root shows no descendants)
        root_section_text = "\n".join(root_section)
        assert "◉  master" in root_section_text, "Root should show master"
        assert "◉  foo" not in root_section_text and "◯  foo" not in root_section_text, (
            f"Root section should NOT show foo (descendant). Root section:\n{root_section_text}"
        )

        # Get foo section lines (from foo header to end)
        foo_section = lines[foo_section_start:]
        foo_section_text = "\n".join(foo_section)

        # Foo section should show both foo (highlighted) and master
        assert "◉  foo" in foo_section_text, "Foo worktree should highlight foo branch"
        assert "◯  master" in foo_section_text, "Foo worktree should show master in stack"


def test_list_with_stacks_hides_descendants_without_worktrees() -> None:
    """
    Descendants without worktrees should not appear in the stack.

    When root is on main with stack [main, feature-1] but no worktree on feature-1:

    EXPECTED:
        root [main]
          ◉  main       <- only main shown, feature-1 hidden (no worktree)
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata with main as parent of feature-1
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main", children=[]),
        }

        # Build fake git ops - only root on main, NO worktree on feature-1
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            current_branches={
                env.cwd: "main",
            },
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)

        # Should only have root section
        assert output.startswith("root")
        assert "◉  main" in output

        # feature-1 should NOT appear (no worktree for it)
        assert "feature-1" not in output, (
            f"feature-1 should be hidden because it has no worktree. Output:\n{output}"
        )


def test_list_with_stacks_shows_descendants_with_gaps() -> None:
    """
    Non-root worktrees show descendants with worktrees (skipping intermediates).
    Root worktree shows only current branch.

    Setup:
        - Stack: main → f1 → f2 → f3
        - Root on main
        - Only worktree on f3 (no worktrees on f1, f2)

    EXPECTED:
        root [main]
          ◉  main       <- only current branch (root shows no descendants)

        f3 [f3]
          ◉  f3
          ◯  f2         <- ancestors always shown for context
          ◯  f1
          ◯  main
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create branch metadata: main → f1 → f2 → f3
        branches = {
            "main": BranchMetadata.trunk("main", children=["f1"]),
            "f1": BranchMetadata.branch("f1", "main", children=["f2"]),
            "f2": BranchMetadata.branch("f2", "f1", children=["f3"]),
            "f3": BranchMetadata.branch("f3", "f2", children=[]),
        }

        # Create f3 worktree
        workstacks_dir = env.workstacks_root / env.cwd.name
        f3_worktree_dir = workstacks_dir / "f3"

        # Build fake git ops - root on main, f3 worktree on f3
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=f3_worktree_dir, branch="f3"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                f3_worktree_dir: env.git_dir,
            },
            current_branches={
                env.cwd: "main",
                f3_worktree_dir: "f3",
            },
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={}),
            use_graphite=True,
            show_pr_info=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)
        lines = output.strip().splitlines()

        # Find the root section and f3 section
        root_section_start = None
        f3_section_start = None
        for i, line in enumerate(lines):
            if line.startswith("root"):
                root_section_start = i
            if line.startswith("f3"):
                f3_section_start = i

        assert root_section_start is not None, "Should have root section"
        assert f3_section_start is not None, "Should have f3 worktree section"

        # Get root section lines (from root header to f3 header)
        root_section = lines[root_section_start:f3_section_start]
        root_section_text = "\n".join(root_section)

        # Root section should show ONLY main (no descendants)
        assert "◉  main" in root_section_text, "Root should show main"
        assert "◉  f3" not in root_section_text and "◯  f3" not in root_section_text, (
            f"Root should NOT show f3 (descendant). Root section:\n{root_section_text}"
        )
        assert "◉  f1" not in root_section_text and "◯  f1" not in root_section_text, (
            f"Root should NOT show f1 (descendant). Root section:\n{root_section_text}"
        )
        assert "◉  f2" not in root_section_text and "◯  f2" not in root_section_text, (
            f"Root should NOT show f2 (descendant). Root section:\n{root_section_text}"
        )

        # Get f3 section lines (from f3 header to end)
        f3_section = lines[f3_section_start:]
        f3_section_text = "\n".join(f3_section)

        # f3 section should show entire stack (ancestors always shown)
        assert "◉  f3" in f3_section_text, "f3 worktree should highlight f3"
        assert "◯  f2" in f3_section_text, "f3 worktree should show f2 (ancestor)"
        assert "◯  f1" in f3_section_text, "f3 worktree should show f1 (ancestor)"
        assert "◯  main" in f3_section_text, "f3 worktree should show main (ancestor)"


def test_list_with_stacks_corrupted_cache() -> None:
    """Corrupted graphite cache should fail fast with JSONDecodeError.

    Per CLAUDE.md fail-fast philosophy: corrupted cache indicates systemic issues
    (CI failure, data corruption, etc.) that should be fixed at the source rather
    than masked with exception handling.
    """
    import pytest

    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Write corrupted JSON to cache file
        (env.git_dir / ".graphite_cache_persist").write_text("{ invalid json }")

        # Build fake git ops
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=RealGraphiteOps(),
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            use_graphite=True,
            show_pr_info=False,
            dry_run=False,
        )

        # Should raise json.JSONDecodeError (fail-fast behavior)
        # Capture expected warning about corrupted cache
        with pytest.warns(UserWarning, match="Cannot parse Graphite cache"):
            with pytest.raises(json.JSONDecodeError):
                runner.invoke(cli, ["list", "--stacks"], obj=test_ctx, catch_exceptions=False)


def test_list_with_stacks_no_plan_file() -> None:
    """Test that missing .plan/ folder doesn't cause errors."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create graphite cache
        graphite_cache = {
            "branches": [
                ["main", {"validationResult": "TRUNK", "children": ["feature"]}],
                ["feature", {"parentBranchName": "main", "children": []}],
            ]
        }
        (env.git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache))

        # Create worktree WITHOUT .plan/ folder
        workstacks_dir = env.workstacks_root / env.cwd.name
        feature_wt = workstacks_dir / "feature"
        feature_wt.mkdir(parents=True)

        # Set up fakes
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
            current_branches={env.cwd: "main", feature_wt: "feature"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops, graphite_ops=RealGraphiteOps(), use_graphite=True, show_pr_info=False
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Should display normally with [no plan] placeholder
        output = strip_ansi(result.output)
        assert "feature" in output
        assert "[no plan]" in output
        assert "◉  feature" in output


def test_list_stacks_shows_plan_title_from_plan_folder() -> None:
    """Test that list --stacks displays plan title from .plan/plan.md (new format)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Mock Graphite cache with simple stack: main → feature
        graphite_cache = {
            "branches": [
                ["main", {"validationResult": "TRUNK", "children": ["feature"]}],
                ["feature", {"parentBranchName": "main", "children": []}],
            ]
        }
        (env.git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache))

        # Create worktree with .plan/ folder (new format)
        workstacks_dir = env.workstacks_root / env.cwd.name
        feature_wt = workstacks_dir / "feature"
        feature_wt.mkdir(parents=True)

        # Create .plan/ folder structure
        plan_folder = feature_wt / ".plan"
        plan_folder.mkdir()

        plan_content = """---
title: OAuth2 Integration Plan
date: 2025-01-15
---

# Implement OAuth2 integration

Detailed implementation plan for OAuth2.

## Steps

1. Set up OAuth provider
2. Implement auth flow
3. Add token management
"""
        (plan_folder / "plan.md").write_text(plan_content, encoding="utf-8")

        # Create progress.md as well (part of new format)
        progress_content = """# Implementation Progress

- [ ] Set up OAuth provider
- [ ] Implement auth flow
- [ ] Add token management
"""
        (plan_folder / "progress.md").write_text(progress_content, encoding="utf-8")

        # Set up fakes
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
            current_branches={env.cwd: "main", feature_wt: "feature"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops, graphite_ops=RealGraphiteOps(), use_graphite=True, show_pr_info=False
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)

        # Plan title (first # heading) from .plan/plan.md should appear
        assert "Implement OAuth2 integration" in output


def test_list_stacks_ignores_legacy_plan_md() -> None:
    """Test that list --stacks does NOT display plan title from .PLAN.md (old format)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Mock Graphite cache with simple stack: main → feature
        graphite_cache = {
            "branches": [
                ["main", {"validationResult": "TRUNK", "children": ["feature"]}],
                ["feature", {"parentBranchName": "main", "children": []}],
            ]
        }
        (env.git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache))

        # Create worktree with .PLAN.md (old format)
        workstacks_dir = env.workstacks_root / env.cwd.name
        feature_wt = workstacks_dir / "feature"
        feature_wt.mkdir(parents=True)

        # Create .PLAN.md with old format
        plan_content = """---
title: Legacy Plan Format
date: 2025-01-15
---

# Old format plan

This should NOT be displayed.
"""
        (feature_wt / ".PLAN.md").write_text(plan_content, encoding="utf-8")

        # Set up fakes
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
            current_branches={env.cwd: "main", feature_wt: "feature"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops, graphite_ops=RealGraphiteOps(), use_graphite=True, show_pr_info=False
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Strip ANSI codes for easier assertion
        output = strip_ansi(result.output)

        # Legacy plan title should NOT appear
        assert "Legacy Plan Format" not in output
