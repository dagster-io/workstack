"""Unit tests for post_progress_comment kit CLI command.

Tests progress comment posting with structured YAML in collapsible details sections.
Uses FakeGitHubIssues from erk package for reliable testing without subprocess mocking.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment import (
    post_progress_comment,
)
from erk.core.github.issues import FakeGitHubIssues, IssueInfo
from erk.integrations.github.metadata_blocks import parse_metadata_blocks

# ============================================================================
# Success Case Tests
# ============================================================================


def test_success_case(tmp_path: Path, monkeypatch) -> None:
    """Test successful progress comment posting."""
    # Setup temp directory structure
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create issue.json
    issue_json = {
        "issue_number": 123,
        "issue_url": "https://github.com/owner/repo/issues/123",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    # Create progress.md with frontmatter
    progress_content = """---
completed_steps: 3
total_steps: 5
---

# Progress

- [x] Step 1
- [x] Step 2
- [x] Step 3
- [ ] Step 4
- [ ] Step 5
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    # Mock subprocess.run to return tmp_path as repo root
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Create fake GitHub issues (inject via context instead of monkeypatch)
    from datetime import UTC, datetime

    fake_issues = FakeGitHubIssues(
        issues={
            123: IssueInfo(
                number=123,
                title="Test Issue",
                body="Test body",
                state="OPEN",
                url="https://github.com/owner/repo/issues/123",
                labels=[],
                assignees=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        }
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command with injected fake
    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Phase 1: Create abstraction"],
        obj=DotAgentContext.for_test(github_issues=fake_issues),
    )

    # Verify exit code
    assert result.exit_code == 0

    # Verify JSON output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["progress"] == "3/5 (60%)"

    # Verify comment was posted
    assert len(fake_issues.added_comments) == 1
    comment_issue_num, comment_body = fake_issues.added_comments[0]
    assert comment_issue_num == 123
    assert "✓ Step 3/5 completed" in comment_body
    assert "<!-- WARNING:" in comment_body

    # Parse metadata block using parse-based validation
    blocks = parse_metadata_blocks(comment_body)
    assert len(blocks) == 1

    block = blocks[0]
    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["total_steps"] == 5
    assert block.data["step_description"] == "Phase 1: Create abstraction"
    assert "timestamp" in block.data
    # Verify percentage is NOT present (removed per refactoring)
    assert "percentage" not in block.data


def test_success_with_different_progress(tmp_path: Path, monkeypatch) -> None:
    """Test progress comment with different completion percentage."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 456,
        "issue_url": "https://github.com/owner/repo/issues/456",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 7
total_steps: 10
---

# Progress
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    from datetime import UTC, datetime

    fake_issues = FakeGitHubIssues(
        issues={
            456: IssueInfo(
                number=456,
                title="Test",
                body="Body",
                state="OPEN",
                url="https://github.com/owner/repo/issues/456",
                labels=[],
                assignees=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        }
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Phase 2 complete"],
        obj=DotAgentContext.for_test(github_issues=fake_issues),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 456
    assert output["progress"] == "7/10 (70%)"

    assert len(fake_issues.added_comments) == 1
    comment_issue_num, comment_body = fake_issues.added_comments[0]
    assert comment_issue_num == 456
    assert "✓ Step 7/10 completed" in comment_body


# ============================================================================
# Error Cases
# ============================================================================


def test_error_not_in_repo(tmp_path: Path, monkeypatch) -> None:
    """Test error when not in a git repository."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Mock subprocess to simulate not in repo
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    assert result.exit_code == 0  # Graceful exit
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "not_in_repo"


def test_error_no_issue_reference(tmp_path: Path, monkeypatch) -> None:
    """Test error when issue.json not found."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    # Don't create issue.json

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    assert result.exit_code == 0  # Graceful exit
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no_issue_reference"


def test_error_no_progress_file(tmp_path: Path, monkeypatch) -> None:
    """Test error when progress.md not found."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 123,
        "issue_url": "https://github.com/owner/repo/issues/123",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")
    # Don't create progress.md

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    assert result.exit_code == 0  # Graceful exit
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no_progress_file"


def test_error_invalid_progress_format(tmp_path: Path, monkeypatch) -> None:
    """Test error when progress.md has invalid frontmatter."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 123,
        "issue_url": "https://github.com/owner/repo/issues/123",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    # Create progress.md with invalid frontmatter
    progress_content = """---
invalid yaml [ : content
---"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    assert result.exit_code == 0  # Graceful exit
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid_progress_format"


def test_error_github_api_failed(tmp_path: Path, monkeypatch) -> None:
    """Test error when GitHub API call fails."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 999,
        "issue_url": "https://github.com/owner/repo/issues/999",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 1
total_steps: 2
---"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Create fake that will raise RuntimeError when add_comment is called
    fake_issues = FakeGitHubIssues(issues={})  # Issue 999 doesn't exist

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
        obj=DotAgentContext.for_test(github_issues=fake_issues),
    )

    assert result.exit_code == 0  # Graceful exit
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "github_api_failed"
