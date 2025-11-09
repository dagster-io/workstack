from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_list_with_stacks_flag() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree for ts-phase-2
        env.create_linked_worktree("ts", "schrockn/ts-phase-2", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(
                    children=["schrockn/ts-phase-1", "sibling-branch"], sha="abc123"
                ),
                "schrockn/ts-phase-1": BranchMetadata.branch(
                    "schrockn/ts-phase-1", children=["schrockn/ts-phase-2"], sha="def456"
                ),
                "schrockn/ts-phase-2": BranchMetadata.branch(
                    "schrockn/ts-phase-2",
                    parent="schrockn/ts-phase-1",
                    children=["schrockn/ts-phase-3"],
                    sha="ghi789",
                ),
                "schrockn/ts-phase-3": BranchMetadata.branch(
                    "schrockn/ts-phase-3", parent="schrockn/ts-phase-2", sha="jkl012"
                ),
                "sibling-branch": BranchMetadata.branch("sibling-branch", sha="mno345"),
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
    with simulated_workstack_env(runner) as env:
        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(sha="abc123"),
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

        result = runner.invoke(cli, ["list", "--stacks"], obj=test_ctx)
        assert result.exit_code == 1
        assert "Error: --stacks requires graphite to be enabled" in result.output


def test_list_with_stacks_no_graphite_cache() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with empty branches (no graphite data)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(sha="abc123"),
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
    with simulated_workstack_env(runner) as env:
        # Create worktree registered to ts-phase-4
        temporal_stack_dir = env.create_linked_worktree(
            "temporal-stack", "schrockn/ts-phase-4", chdir=False
        )

        # Build ops from branches, but set current_branch to ts-phase-3 in temporal-stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["schrockn/ts-phase-1"], sha="abc123"),
                "schrockn/ts-phase-1": BranchMetadata.branch(
                    "schrockn/ts-phase-1", children=["schrockn/ts-phase-2"], sha="def456"
                ),
                "schrockn/ts-phase-2": BranchMetadata.branch(
                    "schrockn/ts-phase-2",
                    parent="schrockn/ts-phase-1",
                    children=["schrockn/ts-phase-3"],
                    sha="ghi789",
                ),
                "schrockn/ts-phase-3": BranchMetadata.branch(
                    "schrockn/ts-phase-3",
                    parent="schrockn/ts-phase-2",
                    children=["schrockn/ts-phase-4"],
                    sha="jkl012",
                ),
                "schrockn/ts-phase-4": BranchMetadata.branch(
                    "schrockn/ts-phase-4", parent="schrockn/ts-phase-3", sha="mno345"
                ),
            },
            current_branch="schrockn/ts-phase-3",  # Actually on phase-3
            current_worktree=temporal_stack_dir,
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
    with simulated_workstack_env(runner) as env:
        # Build ops from branches - trunk is master, foo is child with no worktree
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "master": BranchMetadata.main("master", children=["foo"], sha="abc123"),
                "foo": BranchMetadata.branch("foo", parent="master", sha="def456"),
            },
            current_branch="master",
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
    with simulated_workstack_env(runner) as env:
        # Create foo worktree
        env.create_linked_worktree("foo", "foo", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "master": BranchMetadata.main("master", children=["foo"], sha="abc123"),
                "foo": BranchMetadata.branch("foo", parent="master", sha="def456"),
            },
            current_branch="master",
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
    with simulated_workstack_env(runner) as env:
        # Build ops - feature-1 has no worktree
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", sha="def456"),
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
    with simulated_workstack_env(runner) as env:
        # Create f3 worktree
        env.create_linked_worktree("f3", "f3", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["f1"], sha="abc123"),
                "f1": BranchMetadata.branch("f1", children=["f2"], sha="def456"),
                "f2": BranchMetadata.branch("f2", parent="f1", children=["f3"], sha="ghi789"),
                "f3": BranchMetadata.branch("f3", parent="f2", sha="jkl012"),
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


def test_list_with_stacks_shows_plan_summary() -> None:
    """Test that plan summary appears between worktree header and stack."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree with .PLAN.md
        feature_wt = env.create_linked_worktree("feature", "feature", chdir=False)

        # Create .PLAN.md with frontmatter and heading
        plan_content = """---
title: Feature Implementation
date: 2025-01-15
---

# Implement OAuth2 integration

Some description here.

## Details
More content.
"""
        (feature_wt / ".PLAN.md").write_text(plan_content, encoding="utf-8")

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature"], sha="abc123"),
                "feature": BranchMetadata.branch("feature", sha="def456"),
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

        # Plan title should appear
        assert "Implement OAuth2 integration" in output

        # Verify plan appears on the feature header line
        lines = output.splitlines()
        feature_header_idx = None

        for i, line in enumerate(lines):
            if line.startswith("feature"):
                feature_header_idx = i
                break

        assert feature_header_idx is not None
        # Plan should now appear ON the feature header line
        assert "Implement OAuth2 integration" in lines[feature_header_idx]


def test_list_without_stacks_shows_plan_summary() -> None:
    """Test that plan summary now appears on main line (not just with --stacks)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree with .PLAN.md
        feature_wt = env.create_linked_worktree("feature", "feature", chdir=False)

        # Create .PLAN.md
        (feature_wt / ".PLAN.md").write_text("# Test Plan\n\nContent.", encoding="utf-8")

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature"], sha="abc123"),
                "feature": BranchMetadata.branch("feature", sha="def456"),
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
        output = strip_ansi(result.output)

        # Plan title SHOULD appear on the main line now
        assert "Test Plan" in output


def test_list_with_stacks_no_plan_file() -> None:
    """Test that missing .PLAN.md doesn't cause errors."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree WITHOUT .PLAN.md
        env.create_linked_worktree("feature", "feature", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature"], sha="abc123"),
                "feature": BranchMetadata.branch("feature", sha="def456"),
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

        # Should display normally with [no plan] placeholder
        output = strip_ansi(result.output)
        assert "feature" in output
        assert "[no plan]" in output
        assert "◉  feature" in output


def test_list_with_stacks_plan_without_frontmatter() -> None:
    """Test parsing plan with heading as first line."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree with .PLAN.md (no frontmatter)
        feature_wt = env.create_linked_worktree("feature", "feature", chdir=False)

        plan_content = "# Simple feature implementation\n\nContent here."
        (feature_wt / ".PLAN.md").write_text(plan_content, encoding="utf-8")

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature"], sha="abc123"),
                "feature": BranchMetadata.branch("feature", sha="def456"),
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

        output = strip_ansi(result.output)
        assert "Simple feature implementation" in output
