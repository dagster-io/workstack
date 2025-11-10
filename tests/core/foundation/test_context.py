"""Tests for the WorkstackContext."""

from pathlib import Path

import pytest

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.core.context import WorkstackContext


def test_context_initialization_and_attributes() -> None:
    """Initialization wires through every dependency and exposes them as attributes."""
    git_ops = FakeGitOps()
    global_config_ops = FakeGlobalConfigOps(workstacks_root=Path("/tmp"))
    github_ops = FakeGitHubOps()
    graphite_ops = FakeGraphiteOps()
    shell_ops = FakeShellOps()

    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=shell_ops,
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    assert ctx.git_ops is git_ops
    assert ctx.global_config_ops is global_config_ops
    assert ctx.github_ops is github_ops
    assert ctx.graphite_ops is graphite_ops
    assert ctx.shell_ops is shell_ops
    assert ctx.dry_run is False


def test_context_is_frozen() -> None:
    """WorkstackContext is a frozen dataclass."""
    ctx = WorkstackContext(
        git_ops=FakeGitOps(),
        global_config_ops=FakeGlobalConfigOps(workstacks_root=Path("/tmp")),
        github_ops=FakeGitHubOps(),
        graphite_ops=FakeGraphiteOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=True,
    )

    with pytest.raises(AttributeError):
        ctx.dry_run = False  # type: ignore[misc]
