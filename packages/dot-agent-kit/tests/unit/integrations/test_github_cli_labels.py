"""Unit tests for GitHub CLI label operations."""

from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli


def test_ensure_label_creates_new() -> None:
    """Test label creation when label doesn't exist."""
    fake_gh = FakeDotAgentGitHubCli()

    result = fake_gh.ensure_label_exists("erk-plan", "Description", "0E8A16")

    assert not result.exists
    assert result.created
    assert "erk-plan" in fake_gh.labels


def test_ensure_label_existing() -> None:
    """Test label check when label already exists."""
    fake_gh = FakeDotAgentGitHubCli()

    # Create label first
    fake_gh.ensure_label_exists("erk-plan", "Desc", "0E8A16")

    # Check again
    result = fake_gh.ensure_label_exists("erk-plan", "Desc", "0E8A16")

    assert result.exists
    assert not result.created


def test_ensure_label_multiple_labels() -> None:
    """Test creating multiple different labels."""
    fake_gh = FakeDotAgentGitHubCli()

    result1 = fake_gh.ensure_label_exists("erk-plan", "Plan desc", "0E8A16")
    result2 = fake_gh.ensure_label_exists("erk-queue", "Queue desc", "FF0000")

    assert result1.created
    assert result2.created
    assert "erk-plan" in fake_gh.labels
    assert "erk-queue" in fake_gh.labels


def test_ensure_label_preserves_existing_labels() -> None:
    """Test that creating new label doesn't affect existing ones."""
    fake_gh = FakeDotAgentGitHubCli(labels={"existing-label"})

    result = fake_gh.ensure_label_exists("erk-plan", "Desc", "0E8A16")

    assert result.created
    assert "existing-label" in fake_gh.labels
    assert "erk-plan" in fake_gh.labels


def test_labels_property_returns_copy() -> None:
    """Test that labels property returns a copy, not mutable reference."""
    fake_gh = FakeDotAgentGitHubCli()
    fake_gh.ensure_label_exists("erk-plan", "Desc", "0E8A16")

    labels = fake_gh.labels
    labels.add("should-not-affect-fake")

    assert "should-not-affect-fake" not in fake_gh.labels
    assert "erk-plan" in fake_gh.labels
