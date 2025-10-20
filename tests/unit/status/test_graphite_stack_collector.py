"""Unit tests for GraphiteStackCollector."""

from pathlib import Path
from typing import Any

import pytest

from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from workstack.core.branch_metadata import BranchMetadata
from workstack.status.collectors.graphite import GraphiteStackCollector


def setup_stack_collector(
    tmp_path: Path,
    *,
    branch: str | None,
    use_graphite: bool = True,
    graphite_kwargs: dict[str, Any] | None = None,
    git_kwargs: dict[str, Any] | None = None,
) -> tuple[GraphiteStackCollector, Path, Path, Any]:
    """Create a collector and test context for the requested branch."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    git_ops = FakeGitOps(
        current_branches={worktree_path: branch},
        **(git_kwargs or {}),
    )
    graphite_ops = FakeGraphiteOps(**(graphite_kwargs or {}))
    ctx = create_test_context(
        git_ops=git_ops,
        graphite_ops=graphite_ops,
        global_config_ops=FakeGlobalConfigOps(use_graphite=use_graphite),
    )

    return GraphiteStackCollector(), worktree_path, repo_root, ctx


STACK_CASES = [
    {
        "name": "no_stack_for_branch",
        "branch": "standalone-branch",
        "graphite_kwargs": {"stacks": {}},
        "expected": None,
    },
    {
        "name": "middle_of_stack",
        "branch": "feature-2",
        "graphite_kwargs": {
            "stacks": {
                "feature-2": ["main", "feature-1", "feature-2", "feature-3"],
            }
        },
        "expected": {
            "current_branch": "feature-2",
            "stack": ["main", "feature-1", "feature-2", "feature-3"],
            "parent_branch": "feature-1",
            "children_branches": ["feature-3"],
            "is_trunk": False,
        },
    },
    {
        "name": "top_of_stack",
        "branch": "feature-final",
        "graphite_kwargs": {
            "stacks": {
                "feature-final": ["main", "feature-mid", "feature-final"],
            }
        },
        "expected": {
            "current_branch": "feature-final",
            "parent_branch": "feature-mid",
            "children_branches": [],
            "is_trunk": False,
        },
    },
    {
        "name": "trunk_branch_at_bottom",
        "branch": "main",
        "graphite_kwargs": {
            "stacks": {
                "main": ["main", "feature-1", "feature-2"],
            }
        },
        "expected": {
            "current_branch": "main",
            "parent_branch": None,
            "children_branches": ["feature-1"],
            "is_trunk": True,
        },
    },
    {
        "name": "orphaned_branch",
        "branch": "orphaned",
        "graphite_kwargs": {
            "stacks": {
                "other-branch": ["main", "other-branch", "next-branch"],
            }
        },
        "expected": None,
    },
]


@pytest.mark.parametrize("case", STACK_CASES, ids=lambda case: case["name"])
def test_graphite_stack_collector_collect_from_stacks(tmp_path: Path, case: dict[str, Any]) -> None:
    """Validate stack collection using the stacks data returned by Graphite."""
    collector, worktree_path, repo_root, ctx = setup_stack_collector(
        tmp_path,
        branch=case["branch"],
        graphite_kwargs=case.get("graphite_kwargs"),
    )

    result = collector.collect(ctx, worktree_path, repo_root)
    expected = case["expected"]

    if expected is None:
        assert result is None
        return

    assert result is not None
    for key, value in expected.items():
        assert getattr(result, key) == value


BRANCH_METADATA_CASES = [
    {
        "name": "linear_stack_from_branch_metadata",
        "branch": "feature-2",
        "branches": {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="def456",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=["feature-3"],
                is_trunk=False,
                commit_sha="ghi789",
            ),
            "feature-3": BranchMetadata(
                name="feature-3",
                parent="feature-2",
                children=[],
                is_trunk=False,
                commit_sha="jkl012",
            ),
        },
        "expected": {
            "stack": ["main", "feature-1", "feature-2", "feature-3"],
            "parent_branch": "feature-1",
            "children_branches": ["feature-3"],
            "is_trunk": False,
        },
    },
    {
        "name": "branch_metadata_prefers_first_child",
        "branch": "branch-a",
        "branches": {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["branch-a", "branch-x"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "branch-a": BranchMetadata(
                name="branch-a",
                parent="main",
                children=["branch-b"],
                is_trunk=False,
                commit_sha="def456",
            ),
            "branch-b": BranchMetadata(
                name="branch-b",
                parent="branch-a",
                children=[],
                is_trunk=False,
                commit_sha="ghi789",
            ),
            "branch-x": BranchMetadata(
                name="branch-x",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="xyz999",
            ),
        },
        "expected": {
            "stack": ["main", "branch-a", "branch-b"],
            "parent_branch": "main",
            "children_branches": ["branch-b"],
            "is_trunk": False,
        },
    },
]


@pytest.mark.parametrize(
    "case",
    BRANCH_METADATA_CASES,
    ids=lambda case: case["name"],
)
def test_graphite_stack_collector_from_branch_metadata(
    tmp_path: Path, case: dict[str, Any]
) -> None:
    """Ensure the collector can build stacks using cached BranchMetadata."""

    collector, worktree_path, repo_root, ctx = setup_stack_collector(
        tmp_path,
        branch=case["branch"],
        graphite_kwargs={"branches": case["branches"]},
    )

    result = collector.collect(ctx, worktree_path, repo_root)
    assert result is not None
    for key, value in case["expected"].items():
        assert getattr(result, key) == value


def test_graphite_stack_collector_detached_head(tmp_path: Path) -> None:
    """Detached HEAD state should not produce stack data."""
    collector, worktree_path, repo_root, ctx = setup_stack_collector(
        tmp_path,
        branch=None,
        graphite_kwargs={"stacks": {"feature": ["main", "feature"]}},
    )

    assert collector.collect(ctx, worktree_path, repo_root) is None


@pytest.mark.parametrize(
    ("use_graphite", "path_exists", "expected"),
    [
        (False, True, False),
        (True, False, False),
        (True, True, True),
    ],
    ids=["graphite-disabled", "missing-path", "available"],
)
def test_graphite_stack_collector_is_available(
    tmp_path: Path, use_graphite: bool, path_exists: bool, expected: bool
) -> None:
    """Availability depends on Graphite being enabled and the worktree existing."""
    worktree_path = tmp_path / "worktree"
    if path_exists:
        worktree_path.mkdir()

    ctx = create_test_context(global_config_ops=FakeGlobalConfigOps(use_graphite=use_graphite))
    collector = GraphiteStackCollector()

    assert collector.is_available(ctx, worktree_path) is expected
