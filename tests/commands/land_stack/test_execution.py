"""Tests for land_stack execution module."""

from pathlib import Path

import pytest

from erk.cli.commands.land_stack import execution
from erk.cli.commands.land_stack.execution import MergeabilityUnknownError
from erk.cli.commands.land_stack.retry import retry_with_backoff
from erk.core.context import ErkContext
from erk.core.github.types import PRMergeability
from tests.fakes.github import FakeGitHub
from tests.fakes.time_provider import FakeTime


@pytest.fixture
def check_pr_mergeable():
    """Provide fast version of _check_pr_mergeable_with_retry for tests."""
    # Get the original undecorated function
    # __wrapped__ is added by functools.wraps but pyright doesn't recognize it
    original_func = execution._check_pr_mergeable_with_retry.__wrapped__  # type: ignore[attr-defined]

    # Re-apply decorator with FakeTime for instant tests
    fast_version = retry_with_backoff(
        max_attempts=5,
        base_delay=2.0,
        backoff_factor=2.0,
        time_provider=FakeTime()
    )(original_func)

    return fast_version


def test_check_pr_mergeable_unknown_triggers_retry(check_pr_mergeable) -> None:
    """Test that UNKNOWN status raises exception to trigger retry."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    # UNKNOWN status should raise MergeabilityUnknownError
    with pytest.raises(MergeabilityUnknownError) as exc_info:
        check_pr_mergeable(ctx, repo_root, 123)

    # Verify exception details
    assert exc_info.value.pr_number == 123
    assert "UNKNOWN" in str(exc_info.value)


def test_check_pr_mergeable_unknown_eventually_clean(check_pr_mergeable) -> None:
    """Test that retries succeed when status becomes CLEAN.

    This test simulates GitHub's async merge status recalculation by
    changing the fake's response after the first call.
    """
    # Start with UNKNOWN status
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    # First call should raise
    with pytest.raises(MergeabilityUnknownError):
        check_pr_mergeable(ctx, repo_root, 123)

    # Update fake to return CLEAN (simulating GitHub recalculation)
    github._pr_mergeability[123] = PRMergeability(
        mergeable="MERGEABLE", merge_state_status="CLEAN"
    )

    # Second call should succeed
    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is True
    assert status == "CLEAN"
    assert reason is None


def test_check_pr_mergeable_unknown_exhausts_retries(check_pr_mergeable) -> None:
    """Test that persistent UNKNOWN fails after max attempts.

    The retry decorator should exhaust all 5 attempts and let the
    exception bubble up.
    """
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    # Should raise after exhausting retries
    with pytest.raises(MergeabilityUnknownError) as exc_info:
        check_pr_mergeable(ctx, repo_root, 123)

    assert exc_info.value.pr_number == 123


def test_check_pr_mergeable_clean_status(check_pr_mergeable) -> None:
    """Test that CLEAN status works correctly."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is True
    assert status == "CLEAN"
    assert reason is None


def test_check_pr_mergeable_dirty_status(check_pr_mergeable) -> None:
    """Test that DIRTY status returns conflict error."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is False
    assert status == "DIRTY"
    assert reason is not None
    assert "merge conflicts" in reason


def test_check_pr_mergeable_blocked_status(check_pr_mergeable) -> None:
    """Test that BLOCKED status returns protection error."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="BLOCKED")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is False
    assert status == "BLOCKED"
    assert reason is not None
    assert "branch protection" in reason


def test_check_pr_mergeable_behind_status(check_pr_mergeable) -> None:
    """Test that BEHIND status returns needs update error."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="BEHIND")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is False
    assert status == "BEHIND"
    assert reason is not None
    assert "behind base" in reason


def test_check_pr_mergeable_unstable_status(check_pr_mergeable) -> None:
    """Test that UNSTABLE status returns failing checks error."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNSTABLE")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is False
    assert status == "UNSTABLE"
    assert reason is not None
    assert "failing status checks" in reason


def test_check_pr_mergeable_other_status(check_pr_mergeable) -> None:
    """Test that unknown status values are handled gracefully."""
    github = FakeGitHub(
        pr_mergeability={
            123: PRMergeability(mergeable="UNKNOWN", merge_state_status="WEIRD_STATUS")
        }
    )

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    is_mergeable, status, reason = check_pr_mergeable(ctx, repo_root, 123)

    assert is_mergeable is False
    assert status == "WEIRD_STATUS"
    assert reason is not None
    assert "not in a mergeable state" in reason
    assert "WEIRD_STATUS" in reason  # Status should be in error message


def test_check_pr_mergeable_api_failure(check_pr_mergeable) -> None:
    """Test that API failures raise RuntimeError."""
    # Configure fake to return None (simulating API error)
    github = FakeGitHub(pr_mergeability={123: None})

    ctx = ErkContext.for_test(github=github)
    repo_root = Path("/fake/repo")

    with pytest.raises(RuntimeError) as exc_info:
        check_pr_mergeable(ctx, repo_root, 123)

    assert "Failed to check mergeability" in str(exc_info.value)
    assert "123" in str(exc_info.value)
