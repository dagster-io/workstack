"""Unit tests for GitHubPRCollector."""

from pathlib import Path
from typing import Any

import pytest

from tests.fakes.context import create_test_context
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from workstack.core.github_ops import PullRequestInfo
from workstack.status.collectors.github import GitHubPRCollector


def make_pr(
    *,
    number: int,
    state: str = "OPEN",
    is_draft: bool = False,
    checks_passing: bool | None = None,
    owner: str = "owner",
    repo: str = "repo",
    url: str | None = None,
) -> PullRequestInfo:
    """Create a PullRequestInfo with sensible defaults tailored for tests."""
    pr_url = url or f"https://github.com/{owner}/{repo}/pull/{number}"
    return PullRequestInfo(
        number=number,
        state=state,
        url=pr_url,
        is_draft=is_draft,
        checks_passing=checks_passing,
        owner=owner,
        repo=repo,
    )


def setup_collector(
    tmp_path: Path,
    *,
    branch: str | None,
    prs: dict[str, PullRequestInfo] | None = None,
    show_pr_info: bool = True,
    graphite_kwargs: dict[str, Any] | None = None,
    git_kwargs: dict[str, Any] | None = None,
) -> tuple[GitHubPRCollector, Path, Path, Any]:
    """Build a collector and context for the given branch/PR mapping."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    git_ops_kwargs = git_kwargs or {}
    git_ops = FakeGitOps(
        current_branches={worktree_path: branch},
        **git_ops_kwargs,
    )

    graphite_ops_kwargs = graphite_kwargs or {}
    graphite_ops = FakeGraphiteOps(**graphite_ops_kwargs)

    ctx = create_test_context(
        git_ops=git_ops,
        github_ops=FakeGitHubOps(prs=prs or {}),
        graphite_ops=graphite_ops,
        global_config_ops=FakeGlobalConfigOps(show_pr_info=show_pr_info),
    )

    return GitHubPRCollector(), worktree_path, repo_root, ctx


COLLECT_CASES = [
    {
        "name": "no_matching_pr",
        "branch": "feature-branch",
        "prs": {"other-branch": make_pr(number=456)},
        "expected": None,
    },
    {
        "name": "open_no_checks",
        "branch": "feature-branch",
        "prs": {"feature-branch": make_pr(number=123)},
        "expected": {
            "number": 123,
            "state": "OPEN",
            "is_draft": False,
            "checks_passing": None,
            "ready_to_merge": True,
            "reviews": None,
        },
    },
    {
        "name": "open_passing_checks",
        "branch": "tested-branch",
        "prs": {
            "tested-branch": make_pr(number=789, checks_passing=True),
        },
        "expected": {
            "number": 789,
            "checks_passing": True,
            "ready_to_merge": True,
        },
    },
    {
        "name": "open_failing_checks",
        "branch": "broken-branch",
        "prs": {
            "broken-branch": make_pr(number=999, checks_passing=False),
        },
        "expected": {
            "number": 999,
            "checks_passing": False,
            "ready_to_merge": False,
        },
    },
    {
        "name": "draft_pr",
        "branch": "needs-changes",
        "prs": {
            "needs-changes": make_pr(number=333, is_draft=True, checks_passing=True),
        },
        "expected": {
            "number": 333,
            "is_draft": True,
            "ready_to_merge": False,
        },
    },
    {
        "name": "merged_pr",
        "branch": "merged-branch",
        "prs": {
            "merged-branch": make_pr(number=444, state="MERGED", checks_passing=True),
        },
        "expected": {
            "number": 444,
            "state": "MERGED",
            "ready_to_merge": False,
        },
    },
    {
        "name": "closed_pr",
        "branch": "closed-branch",
        "prs": {
            "closed-branch": make_pr(number=666, state="CLOSED", checks_passing=True),
        },
        "expected": {
            "number": 666,
            "state": "CLOSED",
            "ready_to_merge": False,
        },
    },
    {
        "name": "multiple_prs_prefers_current_branch",
        "branch": "feature-x",
        "prs": {
            "feature-x": make_pr(number=111, checks_passing=True),
            "feature-y": make_pr(number=112, checks_passing=True),
        },
        "expected": {
            "number": 111,
        },
    },
    {
        "name": "detached_head_has_no_pr",
        "branch": None,
        "prs": {
            "feature": make_pr(number=101),
        },
        "expected": None,
    },
    {
        "name": "missing_pr_data_returns_none",
        "branch": "error-branch",
        "prs": {},
        "expected": None,
    },
]


@pytest.mark.parametrize("case", COLLECT_CASES, ids=lambda case: case["name"])
def test_github_pr_collector_collect_cases(tmp_path: Path, case: dict[str, Any]) -> None:
    """Exercise the collector across the common PR scenarios."""
    collector, worktree_path, repo_root, ctx = setup_collector(
        tmp_path,
        branch=case["branch"],
        prs=case.get("prs"),
    )

    result = collector.collect(ctx, worktree_path, repo_root)
    expected = case["expected"]

    if expected is None:
        assert result is None
        return

    assert result is not None
    for key, value in expected.items():
        assert getattr(result, key) == value


def test_github_pr_collector_prefers_graphite_data(tmp_path: Path) -> None:
    """Graphite data should win over GitHub when both sources have PR info."""
    graphite_pr = make_pr(
        number=1001,
        url="https://app.graphite.dev/github/pr/owner/repo/1001",
        checks_passing=None,
    )
    github_pr = make_pr(
        number=1002,
        url="https://github.com/owner/repo/pull/1002",
        checks_passing=True,
    )

    collector, worktree_path, repo_root, ctx = setup_collector(
        tmp_path,
        branch="graphite-branch",
        prs={"graphite-branch": github_pr},
        graphite_kwargs={"pr_info": {"graphite-branch": graphite_pr}},
    )

    result = collector.collect(ctx, worktree_path, repo_root)
    assert result is not None
    assert result.number == 1001
    assert result.url == "https://app.graphite.dev/github/pr/owner/repo/1001"


def test_github_pr_collector_falls_back_to_github(tmp_path: Path) -> None:
    """If Graphite has no data, fall back to GitHub PR details."""
    github_pr = make_pr(number=2001, checks_passing=True)

    collector, worktree_path, repo_root, ctx = setup_collector(
        tmp_path,
        branch="github-only-branch",
        prs={"github-only-branch": github_pr},
        graphite_kwargs={"pr_info": {}},
    )

    result = collector.collect(ctx, worktree_path, repo_root)
    assert result is not None
    assert result.number == 2001


@pytest.mark.parametrize(
    ("show_pr_info", "path_exists", "expected"),
    [
        (False, True, False),
        (True, False, False),
        (True, True, True),
    ],
    ids=["feature-disabled", "path-missing", "available"],
)
def test_github_pr_collector_is_available(
    tmp_path: Path, show_pr_info: bool, path_exists: bool, expected: bool
) -> None:
    """Availability is controlled by config and worktree presence."""
    worktree_path = tmp_path / "worktree"
    if path_exists:
        worktree_path.mkdir()

    ctx = create_test_context(global_config_ops=FakeGlobalConfigOps(show_pr_info=show_pr_info))
    collector = GitHubPRCollector()

    assert collector.is_available(ctx, worktree_path) is expected
