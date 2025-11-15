"""Tests for the WorkstackContext."""

from pathlib import Path

import pytest

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils import sentinel_path
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.repo_discovery import RepoContext


def test_context_initialization_and_attributes() -> None:
    """Initialization wires through every dependency and exposes them as attributes."""
    git_ops = FakeGitOps()
    github_ops = FakeGitHubOps()
    graphite_ops = FakeGraphiteOps()
    shell_ops = FakeShellOps()
    global_config = GlobalConfig(
        workstacks_root=Path("/tmp"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
    )

    ctx = WorkstackContext.for_test(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=shell_ops,
        cwd=sentinel_path(),
        global_config=global_config,
        dry_run=False,
    )

    assert ctx.git_ops is git_ops
    assert ctx.global_config == global_config
    assert ctx.github_ops is github_ops
    assert ctx.graphite_ops is graphite_ops
    assert ctx.shell_ops is shell_ops
    assert ctx.dry_run is False


def test_context_is_frozen() -> None:
    """WorkstackContext is a frozen dataclass."""
    global_config = GlobalConfig(
        workstacks_root=Path("/tmp"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
    )
    ctx = WorkstackContext.for_test(
        git_ops=FakeGitOps(),
        global_config=global_config,
        github_ops=FakeGitHubOps(),
        graphite_ops=FakeGraphiteOps(),
        shell_ops=FakeShellOps(),
        cwd=sentinel_path(),
        dry_run=True,
    )

    with pytest.raises(AttributeError):
        ctx.dry_run = False  # type: ignore[misc]


def test_minimal_factory_creates_context_with_git_ops() -> None:
    """WorkstackContext.minimal() creates context with only git_ops configured."""
    git_ops = FakeGitOps(
        current_branches={Path("/repo"): "main"},
        default_branches={Path("/repo"): "main"},
    )
    cwd = sentinel_path()

    ctx = WorkstackContext.minimal(git_ops, cwd)

    assert ctx.git_ops is git_ops
    assert ctx.cwd == cwd
    assert ctx.dry_run is False
    assert ctx.trunk_branch is None
    assert ctx.global_config is None


def test_minimal_factory_with_dry_run() -> None:
    """WorkstackContext.minimal() respects dry_run parameter."""
    git_ops = FakeGitOps()
    cwd = sentinel_path()

    ctx = WorkstackContext.minimal(git_ops, cwd, dry_run=True)

    assert ctx.dry_run is True


def test_minimal_factory_creates_fake_ops() -> None:
    """WorkstackContext.minimal() initializes other ops with fakes."""
    git_ops = FakeGitOps()
    cwd = sentinel_path()

    ctx = WorkstackContext.minimal(git_ops, cwd)

    # All other ops should be fake implementations
    assert isinstance(ctx.github_ops, FakeGitHubOps)
    assert isinstance(ctx.graphite_ops, FakeGraphiteOps)
    assert isinstance(ctx.shell_ops, FakeShellOps)


def test_for_test_factory_creates_context_with_defaults() -> None:
    """WorkstackContext.for_test() creates context with all defaults when no args provided."""
    ctx = WorkstackContext.for_test()

    assert isinstance(ctx.git_ops, FakeGitOps)
    assert isinstance(ctx.github_ops, FakeGitHubOps)
    assert isinstance(ctx.graphite_ops, FakeGraphiteOps)
    assert isinstance(ctx.shell_ops, FakeShellOps)
    assert ctx.cwd == sentinel_path()
    assert ctx.dry_run is False
    assert ctx.trunk_branch is None


def test_for_test_factory_accepts_custom_ops() -> None:
    """WorkstackContext.for_test() uses provided ops instead of defaults."""
    git_ops = FakeGitOps(
        current_branches={Path("/repo"): "main"},
        default_branches={Path("/repo"): "main"},
    )
    github_ops = FakeGitHubOps()
    cwd = Path("/custom/cwd")

    ctx = WorkstackContext.for_test(
        git_ops=git_ops,
        github_ops=github_ops,
        cwd=cwd,
    )

    assert ctx.git_ops is git_ops
    assert ctx.github_ops is github_ops
    assert ctx.cwd == cwd


def test_for_test_factory_accepts_trunk_branch() -> None:
    """WorkstackContext.for_test() computes trunk_branch from git_ops."""
    git_ops = FakeGitOps(trunk_branches={Path("/repo"): "develop"})
    ctx = WorkstackContext.for_test(
        git_ops=git_ops,
        repo=RepoContext(
            root=Path("/repo"),
            repo_name="repo",
            workstacks_dir=Path("/repo/.workstacks"),
        ),
    )

    assert ctx.trunk_branch == "develop"
