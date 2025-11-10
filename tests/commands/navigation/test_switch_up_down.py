"""Tests for workstack switch --up and --down navigation."""

import json
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.gitops import WorktreeInfo


def setup_graphite_stack(
    git_dir: Path, branches: dict[str, dict[str, list[str] | str | bool | None]]
) -> None:
    """Set up a fake Graphite cache file with a stack structure.

    Args:
        git_dir: Path to .git directory
        branches: Dict mapping branch name to metadata with keys:
            - parent: parent branch name or None for trunk
            - children: list of child branch names
            - is_trunk: optional bool, defaults to False
    """
    cache_file = git_dir / ".graphite_cache_persist"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    branches_data = []
    for branch_name, metadata in branches.items():
        branch_data = {
            "children": metadata.get("children", []),
        }
        if metadata.get("parent") is not None:
            branch_data["parentBranchName"] = metadata["parent"]
        if metadata.get("is_trunk", False):
            branch_data["validationResult"] = "TRUNK"

        branches_data.append([branch_name, branch_data])

    cache_data = {"branches": branches_data}
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")


def test_switch_up_with_existing_worktree() -> None:
    """Test --up navigation when child branch has a worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1 -> feature-2
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        # Set up worktrees
        feature_1_path = workstacks_dir / "feature-1"
        feature_1_path.mkdir(parents=True, exist_ok=True)

        # The test runs from cwd, so we simulate being in feature-1 by setting
        # cwd's current branch to feature-1
        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={
                cwd: "feature-1",  # Simulate being in feature-1 worktree
            },
            default_branches={cwd: "main"},
            git_common_dirs={
                cwd: git_dir,
            },
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Switch up from feature-1 to feature-2
        # Run from feature-1 worktree
        (workstacks_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            cli, ["switch", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0
        # Should generate script for feature-2
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "feature-2") in script_content


def test_switch_up_at_top_of_stack() -> None:
    """Test --up navigation when at the top of stack (no children)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1 -> feature-2 (at top)
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={cwd: "feature-2"},  # Simulate being in feature-2 worktree
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["switch", "--up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the top of the stack" in result.stderr


def test_switch_up_child_has_no_worktree() -> None:
    """Test --up navigation when child branch exists but has no worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1 -> feature-2
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        # Only feature-1 has a worktree, feature-2 does not
        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                ]
            },
            current_branches={cwd: "feature-1"},  # Simulate being in feature-1 worktree
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["switch", "--up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-2" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-2" in result.stderr


def test_switch_down_with_existing_worktree() -> None:
    """Test --down navigation when parent branch has a worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1 -> feature-2
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        # Set up worktrees
        (workstacks_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["switch", "--down", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should generate script for feature-1
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "feature-1") in script_content


def test_switch_down_to_trunk_root() -> None:
    """Test --down navigation when parent is trunk checked out in root."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": []},
            },
        )

        # Main is checked out in root, feature-1 has its own worktree
        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                ]
            },
            current_branches={cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Switch down from feature-1 to root (main)
        (workstacks_dir / "feature-1").mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            cli, ["switch", "--down", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should generate script for root
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(cwd) in script_content
        assert "root" in script_content.lower()


def test_switch_down_at_trunk() -> None:
    """Test --down navigation when already at trunk."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main (only trunk)
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": [], "is_trunk": True},
            },
        )

        git_ops = FakeGitOps(
            worktrees={cwd: [WorktreeInfo(path=cwd, branch="main")]},
            current_branches={cwd: "main"},
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["switch", "--down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the bottom of the stack" in result.stderr
        assert "trunk branch 'main'" in result.stderr


def test_switch_down_parent_has_no_worktree() -> None:
    """Test --down navigation when parent branch exists but has no worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature-1 -> feature-2
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        # Only feature-2 has a worktree, feature-1 does not
        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["switch", "--down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-1" in result.stderr or "parent branch" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-1" in result.stderr


def test_switch_graphite_not_enabled() -> None:
    """Test --up/--down require Graphite to be enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(
            worktrees={cwd: [WorktreeInfo(path=cwd, branch="main")]},
            current_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        # Graphite is NOT enabled
        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Try --up
        result = runner.invoke(cli, ["switch", "--up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "workstack config set use_graphite true" in result.stderr

        # Try --down
        result = runner.invoke(cli, ["switch", "--down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr


def test_switch_up_and_down_mutually_exclusive() -> None:
    """Test that --up and --down cannot be used together."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(
            worktrees={cwd: [WorktreeInfo(path=cwd, branch="main")]},
            current_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["switch", "--up", "--down"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Cannot use both --up and --down" in result.stderr


def test_switch_name_with_up_mutually_exclusive() -> None:
    """Test that NAME and --up cannot be used together."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(
            worktrees={cwd: [WorktreeInfo(path=cwd, branch="main")]},
            current_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["switch", "feature-1", "--up"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Cannot specify NAME with --up or --down" in result.stderr


def test_switch_detached_head() -> None:
    """Test --up/--down fail gracefully on detached HEAD."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Current branch is None (detached HEAD)
        git_ops = FakeGitOps(
            worktrees={cwd: [WorktreeInfo(path=cwd, branch=None)]},
            current_branches={cwd: None},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["switch", "--up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_switch_up_with_mismatched_worktree_name() -> None:
    """Test switch --up when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature/db -> feature/db-tests
        # Branch names contain slashes, but worktree dirs use different names
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature/db"], "is_trunk": True},
                "feature/db": {"parent": "main", "children": ["feature/db-tests"]},
                "feature/db-tests": {"parent": "feature/db", "children": []},
            },
        )

        # Worktree directories use different naming than branch names
        # Branch: feature/db -> Worktree: db-refactor
        # Branch: feature/db-tests -> Worktree: db-tests-implementation
        (workstacks_dir / "db-refactor").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "db-tests-implementation").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "db-refactor", branch="feature/db"),
                    WorktreeInfo(
                        path=workstacks_dir / "db-tests-implementation", branch="feature/db-tests"
                    ),
                ]
            },
            current_branches={cwd: "feature/db"},  # Simulate being in feature/db worktree
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Navigate up from feature/db to feature/db-tests using switch --up
        # This would fail before the fix because it would try to find a worktree named
        # "feature/db-tests" instead of resolving to "db-tests-implementation"
        result = runner.invoke(
            cli, ["switch", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for db-tests-implementation (not feature/db-tests)
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "db-tests-implementation") in script_content


def test_switch_down_with_mismatched_worktree_name() -> None:
    """Test switch --down when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        workstacks_dir = cwd / "workstacks" / cwd.name
        workstacks_dir.mkdir(parents=True)
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Set up stack: main -> feature/api -> feature/api-v2
        # Branch names contain slashes, but worktree dirs use different names
        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature/api"], "is_trunk": True},
                "feature/api": {"parent": "main", "children": ["feature/api-v2"]},
                "feature/api-v2": {"parent": "feature/api", "children": []},
            },
        )

        # Worktree directories use different naming than branch names
        # Branch: feature/api -> Worktree: api-work
        # Branch: feature/api-v2 -> Worktree: api-v2-work
        (workstacks_dir / "api-work").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "api-v2-work").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "api-work", branch="feature/api"),
                    WorktreeInfo(path=workstacks_dir / "api-v2-work", branch="feature/api-v2"),
                ]
            },
            current_branches={cwd: "feature/api-v2"},  # Simulate being in feature/api-v2 worktree
            default_branches={cwd: "main"},
            git_common_dirs={cwd: git_dir},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Navigate down from feature/api-v2 to feature/api using switch --down
        # This would fail before the fix because it would try to find a worktree named
        # "feature/api" instead of resolving to "api-work"
        result = runner.invoke(
            cli, ["switch", "--down", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for api-work (not feature/api)
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "api-work") in script_content
