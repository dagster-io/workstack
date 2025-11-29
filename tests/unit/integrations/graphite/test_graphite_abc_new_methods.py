"""Unit tests for new Graphite ABC methods (Layer 1: Fake infrastructure tests).

Tests the four new methods added to the Graphite ABC:
- restack_with_result()
- squash_commits()
- submit()
- navigate_to_child()

These tests verify the fake implementation works correctly.
"""

from pathlib import Path

from erk_shared.integrations.graphite.types import CommandResult
from tests.fakes.graphite import FakeGraphite


def test_restack_with_result_success() -> None:
    """Test restack_with_result() returns configured success result."""
    result = CommandResult(success=True, stdout="Restacked successfully", stderr="")
    fake = FakeGraphite(restack_result=result)

    actual = fake.restack_with_result(Path("/fake/repo"))

    assert actual == result
    assert actual.success is True
    assert actual.stdout == "Restacked successfully"
    assert actual.stderr == ""


def test_restack_with_result_failure() -> None:
    """Test restack_with_result() returns configured failure result."""
    result = CommandResult(success=False, stdout="", stderr="Restack failed: conflicts")
    fake = FakeGraphite(restack_result=result)

    actual = fake.restack_with_result(Path("/fake/repo"))

    assert actual == result
    assert actual.success is False
    assert actual.stderr == "Restack failed: conflicts"


def test_restack_with_result_default() -> None:
    """Test restack_with_result() returns success by default."""
    fake = FakeGraphite()

    actual = fake.restack_with_result(Path("/fake/repo"))

    assert actual.success is True
    assert actual.stdout == ""
    assert actual.stderr == ""


def test_squash_commits_success() -> None:
    """Test squash_commits() returns configured success result."""
    result = CommandResult(success=True, stdout="Squashed 3 commits", stderr="")
    fake = FakeGraphite(squash_result=result)

    actual = fake.squash_commits(Path("/fake/repo"))

    assert actual == result
    assert actual.success is True
    assert actual.stdout == "Squashed 3 commits"


def test_squash_commits_failure() -> None:
    """Test squash_commits() returns configured failure result."""
    result = CommandResult(success=False, stdout="", stderr="Squash failed: no commits")
    fake = FakeGraphite(squash_result=result)

    actual = fake.squash_commits(Path("/fake/repo"))

    assert actual == result
    assert actual.success is False
    assert actual.stderr == "Squash failed: no commits"


def test_squash_commits_default() -> None:
    """Test squash_commits() returns success by default."""
    fake = FakeGraphite()

    actual = fake.squash_commits(Path("/fake/repo"))

    assert actual.success is True


def test_submit_success() -> None:
    """Test submit() returns configured success result."""
    result = CommandResult(success=True, stdout="PR created: #123", stderr="")
    fake = FakeGraphite(submit_result=result)

    actual = fake.submit(Path("/fake/repo"), publish=True, restack=False)

    assert actual == result
    assert actual.success is True
    assert actual.stdout == "PR created: #123"


def test_submit_failure() -> None:
    """Test submit() returns configured failure result."""
    result = CommandResult(success=False, stdout="", stderr="Submit failed: auth required")
    fake = FakeGraphite(submit_result=result)

    actual = fake.submit(Path("/fake/repo"), publish=False, restack=True)

    assert actual == result
    assert actual.success is False
    assert actual.stderr == "Submit failed: auth required"


def test_submit_default() -> None:
    """Test submit() returns success by default."""
    fake = FakeGraphite()

    actual = fake.submit(Path("/fake/repo"), publish=False, restack=False)

    assert actual.success is True


def test_navigate_to_child_success() -> None:
    """Test navigate_to_child() returns True when configured."""
    fake = FakeGraphite(navigate_to_child_success=True)

    actual = fake.navigate_to_child(Path("/fake/repo"))

    assert actual is True


def test_navigate_to_child_failure() -> None:
    """Test navigate_to_child() returns False when configured."""
    fake = FakeGraphite(navigate_to_child_success=False)

    actual = fake.navigate_to_child(Path("/fake/repo"))

    assert actual is False


def test_navigate_to_child_default() -> None:
    """Test navigate_to_child() returns True by default."""
    fake = FakeGraphite()

    actual = fake.navigate_to_child(Path("/fake/repo"))

    assert actual is True
