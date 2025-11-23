"""Unit tests for create_wt_from_issue kit CLI command.

Tests worktree creation from GitHub issues with erk-plan label.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_wt_from_issue import (
    create_wt_from_issue,
    get_repo_root,
    has_erk_plan_label,
)

# ============================================================================
# 1. Helper Function Tests (8 tests)
# ============================================================================


def test_get_repo_root_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test get_repo_root returns Path when in git repo."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    repo_root = get_repo_root()
    assert repo_root == tmp_path


def test_get_repo_root_not_in_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_repo_root returns None when not in git repo."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "fatal: not a git repository"
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    repo_root = get_repo_root()
    assert repo_root is None


def test_has_erk_plan_label_true() -> None:
    """Test has_erk_plan_label returns True when label present."""
    issue_data = {
        "labels": [
            {"name": "bug"},
            {"name": "erk-plan"},
            {"name": "enhancement"},
        ]
    }
    assert has_erk_plan_label(issue_data) is True


def test_has_erk_plan_label_false() -> None:
    """Test has_erk_plan_label returns False when label missing."""
    issue_data = {"labels": [{"name": "bug"}, {"name": "enhancement"}]}
    assert has_erk_plan_label(issue_data) is False


def test_has_erk_plan_label_no_labels() -> None:
    """Test has_erk_plan_label returns False when no labels."""
    issue_data = {"labels": []}
    assert has_erk_plan_label(issue_data) is False


def test_has_erk_plan_label_malformed() -> None:
    """Test has_erk_plan_label handles malformed label data."""
    issue_data = {"labels": "not-a-list"}
    assert has_erk_plan_label(issue_data) is False


def test_has_erk_plan_label_none_labels() -> None:
    """Test has_erk_plan_label handles None labels."""
    issue_data = {"labels": None}
    assert has_erk_plan_label(issue_data) is False


def test_has_erk_plan_label_missing_key() -> None:
    """Test has_erk_plan_label handles missing labels key."""
    issue_data = {}
    assert has_erk_plan_label(issue_data) is False


# ============================================================================
# 2. Success Case Tests (3 tests)
# ============================================================================


def test_create_from_issue_number_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test creating worktree from plain issue number."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    impl_dir = worktree_dir / ".impl"
    impl_dir.mkdir()

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 123})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 123,
                    "title": "Test Issue",
                    "body": "# Plan\n\nImplementation details",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/123",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps(
                {
                    "status": "success",
                    "worktree_name": "feature-branch",
                    "worktree_path": str(worktree_dir),
                    "branch_name": "issue-123-25-11-22",
                }
            )
        elif cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            pass  # Success

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["123"])

    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output
    assert "issue #123" in result.output
    assert "feature-branch" in result.output


def test_create_from_github_url_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test creating worktree from full GitHub URL."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    impl_dir = worktree_dir / ".impl"
    impl_dir.mkdir()

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 456})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 456,
                    "title": "Test Issue",
                    "body": "# Plan\n\nImplementation details",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/456",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps(
                {
                    "status": "success",
                    "worktree_name": "feature-branch",
                    "worktree_path": str(worktree_dir),
                    "branch_name": "issue-456-25-11-22",
                }
            )
        elif cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            pass  # Success

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["https://github.com/owner/repo/issues/456"])

    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output
    assert "issue #456" in result.output


def test_graceful_degradation_comment_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test worktree created successfully even if comment posting fails."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    impl_dir = worktree_dir / ".impl"
    impl_dir.mkdir()

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()

        if cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            result.returncode = 1  # Comment fails
            result.stderr = "gh: authentication required"
        else:
            result.returncode = 0
            if cmd[0] == "git":
                result.stdout = str(tmp_path)
            elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
                result.stdout = json.dumps({"success": True, "issue_number": 789})
            elif cmd[0] == "gh":
                result.stdout = json.dumps(
                    {
                        "number": 789,
                        "title": "Test Issue",
                        "body": "# Plan\n\nImplementation details",
                        "state": "open",
                        "url": "https://github.com/owner/repo/issues/789",
                        "labels": [{"name": "erk-plan"}],
                    }
                )
            elif cmd[0] == "erk":
                result.stdout = json.dumps(
                    {
                        "status": "success",
                        "worktree_name": "feature-branch",
                        "worktree_path": str(worktree_dir),
                        "branch_name": "issue-789-25-11-22",
                    }
                )

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["789"])

    # Still succeeds
    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output
    # But shows warning
    assert "Warning:" in result.output
    assert "Failed to post comment" in result.output


# ============================================================================
# 3. Error Case Tests (8 tests)
# ============================================================================


def test_invalid_issue_reference(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when issue reference is invalid."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.returncode = 1
            result.stdout = json.dumps(
                {
                    "success": False,
                    "error": "invalid_format",
                    "message": "Issue reference must be a number or GitHub URL",
                }
            )

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["invalid"])

    assert result.exit_code == 1
    assert "Failed to parse issue reference" in result.output


def test_not_in_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test command fails when not in git repository."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        if cmd[0] == "git":
            result.returncode = 1
        else:
            result.returncode = 0
        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["123"])

    assert result.exit_code == 1
    assert "Not in a git repository" in result.output


def test_issue_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when GitHub issue doesn't exist."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()

        if cmd[0] == "git":
            result.returncode = 0
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.returncode = 0
            result.stdout = json.dumps({"success": True, "issue_number": 99999})
        elif cmd[0] == "gh":
            result.returncode = 1  # Issue not found
            result.stderr = "issue not found"
        else:
            result.returncode = 0

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["99999"])

    assert result.exit_code == 1
    assert "Failed to fetch issue #99999" in result.output


def test_missing_erk_plan_label(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when issue lacks erk-plan label."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 100})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 100,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/100",
                    "labels": [{"name": "bug"}, {"name": "enhancement"}],  # No erk-plan
                }
            )

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["100"])

    assert result.exit_code == 1
    assert "does not have the 'erk-plan' label" in result.output
    assert "Current labels: bug, enhancement" in result.output


def test_gh_cli_not_authenticated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when gh not authenticated."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()

        if cmd[0] == "git":
            result.returncode = 0
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.returncode = 0
            result.stdout = json.dumps({"success": True, "issue_number": 200})
        elif cmd[0] == "gh":
            result.returncode = 1
            result.stderr = "authentication required"
        else:
            result.returncode = 0

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["200"])

    assert result.exit_code == 1
    assert "Failed to fetch issue #200" in result.output
    assert "gh CLI is authenticated" in result.output


def test_erk_create_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when erk create command fails."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 300})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 300,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/300",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.returncode = 1  # erk create fails
            result.stderr = "Error: Invalid plan format"

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["300"])

    assert result.exit_code == 1
    assert "Failed to create worktree" in result.output


def test_worktree_already_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when worktree already exists."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 400})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 400,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/400",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps({"status": "exists"})  # Worktree exists

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["400"])

    assert result.exit_code == 1
    assert "Failed to create worktree" in result.output


def test_issue_with_empty_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test command fails when issue has no body content."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 500})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 500,
                    "title": "Test Issue",
                    "body": "",  # Empty body
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/500",
                    "labels": [{"name": "erk-plan"}],
                }
            )

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["500"])

    assert result.exit_code == 1
    assert "has no body content" in result.output


# ============================================================================
# 4. Edge Case Tests (4 tests)
# ============================================================================


def test_issue_with_no_labels(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test handling issue with empty labels array."""

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 600})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 600,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/600",
                    "labels": [],  # No labels
                }
            )

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["600"])

    assert result.exit_code == 1
    assert "does not have the 'erk-plan' label" in result.output
    assert "Current labels: none" in result.output


def test_issue_with_special_chars_in_title(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test handling Unicode and special characters in title."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    impl_dir = worktree_dir / ".impl"
    impl_dir.mkdir()

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 700})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 700,
                    "title": 'Test: Add 🎉 emoji support & "quotes"',
                    "body": "# Plan\n\nImplementation details",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/700",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps(
                {
                    "status": "success",
                    "worktree_name": "feature-branch",
                    "worktree_path": str(worktree_dir),
                    "branch_name": "issue-700-25-11-22",
                }
            )
        elif cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            pass  # Success

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["700"])

    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output


def test_multiple_labels_including_erk_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test label detection with multiple labels."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    impl_dir = worktree_dir / ".impl"
    impl_dir.mkdir()

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 800})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 800,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/800",
                    "labels": [
                        {"name": "bug"},
                        {"name": "erk-plan"},
                        {"name": "enhancement"},
                        {"name": "high-priority"},
                    ],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps(
                {
                    "status": "success",
                    "worktree_name": "feature-branch",
                    "worktree_path": str(worktree_dir),
                    "branch_name": "issue-800-25-11-22",
                }
            )
        elif cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            pass  # Success

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["800"])

    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output


def test_save_issue_reference_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test warning when issue.json can't be written (non-fatal)."""
    worktree_dir = tmp_path / "feature-branch"
    worktree_dir.mkdir()
    # Don't create .impl dir - will cause save to fail

    def mock_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 0

        if cmd[0] == "git":
            result.stdout = str(tmp_path)
        elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
            result.stdout = json.dumps({"success": True, "issue_number": 900})
        elif cmd[0] == "gh":
            result.stdout = json.dumps(
                {
                    "number": 900,
                    "title": "Test Issue",
                    "body": "# Plan\n\nDetails",
                    "state": "open",
                    "url": "https://github.com/owner/repo/issues/900",
                    "labels": [{"name": "erk-plan"}],
                }
            )
        elif cmd[0] == "erk":
            result.stdout = json.dumps(
                {
                    "status": "success",
                    "worktree_name": "feature-branch",
                    "worktree_path": str(worktree_dir),
                    "branch_name": "issue-900-25-11-22",
                }
            )
        elif cmd[0] == "dot-agent" and "comment-worktree-creation" in cmd:
            pass  # Success

        return result

    monkeypatch.setattr("subprocess.run", mock_run)

    runner = CliRunner()
    result = runner.invoke(create_wt_from_issue, ["900"])

    # Still succeeds
    assert result.exit_code == 0
    assert "✅ Worktree created" in result.output
