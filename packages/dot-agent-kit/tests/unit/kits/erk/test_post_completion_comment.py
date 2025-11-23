"""Unit tests for post_completion_comment kit CLI command.

Tests completion comment posting with structured YAML in collapsible details sections.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import yaml
from click.testing import CliRunner

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_completion_comment import (
    post_completion_comment,
)
from erk.core.github.issues import FakeGitHubIssues
from erk.integrations.github.metadata_blocks import parse_metadata_blocks

# ============================================================================
# 1. Success Case Tests (1 test)
# ============================================================================


def test_success_case_complete(tmp_path: Path, monkeypatch) -> None:
    """Test successful completion comment posting."""
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

    # Create progress.md with 100% completion
    progress_content = """---
completed_steps: 5
total_steps: 5
---

# Progress

- [x] Step 1
- [x] Step 2
- [x] Step 3
- [x] Step 4
- [x] Step 5
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    # Mock subprocess.run to return tmp_path as repo root
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Create FakeGitHubIssues and inject via context
    fake_issues = FakeGitHubIssues(
        issues={
            123: MagicMock(
                number=123,
                title="Test Issue",
                body="Test body",
                state="OPEN",
            )
        }
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command with injected fake
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Added progress tracking with structured YAML comments"],
        obj=DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path),
    )

    # Verify exit code
    assert result.exit_code == 0

    # Verify JSON output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123

    # Verify comment was posted
    assert len(fake_issues.added_comments) == 1
    comment_number, comment_body = fake_issues.added_comments[0]
    assert comment_number == 123

    # Verify comment format
    assert "✅ Implementation complete" in comment_body
    assert "<!-- WARNING:" in comment_body

    # Parse metadata block using parse-based validation
    blocks = parse_metadata_blocks(comment_body)
    assert len(blocks) == 1

    block = blocks[0]
    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "complete"
    assert block.data["completed_steps"] == 5
    assert block.data["total_steps"] == 5
    assert block.data["summary"] == "Added progress tracking with structured YAML comments"
    assert "timestamp" in block.data


# ============================================================================
# 2. Not Complete Error Test (1 test)
# ============================================================================


def test_not_complete_error(tmp_path: Path, monkeypatch) -> None:
    """Test error when plan is not 100% complete."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create issue.json
    issue_json = {
        "issue_number": 456,
        "issue_url": "https://github.com/owner/repo/issues/456",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    # Create progress.md with 60% completion
    progress_content = """---
completed_steps: 3
total_steps: 5
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Test summary"],
        obj=DotAgentContext.for_test(repo_root=tmp_path),
    )

    # Verify exit code 0 (graceful degradation)
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "not_complete"
    assert "3/5" in output["message"]


# ============================================================================
# 3. Other Error Case Tests (5 tests)
# ============================================================================


def test_no_issue_reference(tmp_path: Path, monkeypatch) -> None:
    """Test error when .impl/issue.json missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Test"],
        obj=DotAgentContext.for_test(repo_root=tmp_path),
    )

    # Verify exit code 0 (graceful degradation)
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no_issue_reference"


def test_no_progress_file(tmp_path: Path, monkeypatch) -> None:
    """Test error when .impl/progress.md missing."""
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

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Test"],
        obj=DotAgentContext.for_test(repo_root=tmp_path),
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no_progress_file"


def test_invalid_progress_format(tmp_path: Path, monkeypatch) -> None:
    """Test error when progress.md has malformed frontmatter."""
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

    # Create progress.md with malformed YAML
    (impl_dir / "progress.md").write_text("Not valid YAML frontmatter", encoding="utf-8")

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Test"],
        obj=DotAgentContext.for_test(repo_root=tmp_path),
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid_progress_format"


def test_github_api_failure(tmp_path: Path, monkeypatch) -> None:
    """Test error when GitHub API fails."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create issue.json
    issue_json = {
        "issue_number": 999,
        "issue_url": "https://github.com/owner/repo/issues/999",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    # Create progress.md with 100% completion
    progress_content = """---
completed_steps: 4
total_steps: 4
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Create FakeGitHubIssues (empty - issue 999 doesn't exist)
    fake_issues = FakeGitHubIssues(issues={})

    monkeypatch.chdir(tmp_path)

    # Run command with injected fake
    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Test"],
        obj=DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path),
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "github_api_failed"
    assert "999" in output["message"]


# ============================================================================
# 4. Edge Case Tests (3 tests)
# ============================================================================


def test_edge_case_unicode_in_summary(tmp_path: Path, monkeypatch) -> None:
    """Test with Unicode characters in summary."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 300,
        "issue_url": "https://github.com/owner/repo/issues/300",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 3
total_steps: 3
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={300: MagicMock(number=300)})

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Implémentation complète"],
        obj=DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify YAML is valid
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)
    assert parsed_yaml["summary"] == "Implémentation complète"


def test_edge_case_colon_in_summary(tmp_path: Path, monkeypatch) -> None:
    """Test YAML escaping with colon in summary."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 400,
        "issue_url": "https://github.com/owner/repo/issues/400",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 4
total_steps: 4
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={400: MagicMock(number=400)})

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Summary: Complete feature"],
        obj=DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path),
    )

    assert result.exit_code == 0

    # Verify YAML is valid and colon is properly escaped
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)
    assert parsed_yaml["summary"] == "Summary: Complete feature"


def test_edge_case_quotes_in_summary(tmp_path: Path, monkeypatch) -> None:
    """Test YAML escaping with quotes in summary."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 500,
        "issue_url": "https://github.com/owner/repo/issues/500",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 2
total_steps: 2
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={500: MagicMock(number=500)})

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_completion_comment,
        ["--summary", "Added 'new' feature"],
        obj=DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path),
    )

    assert result.exit_code == 0

    # Verify YAML is valid and quotes are properly escaped
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)
    assert parsed_yaml["summary"] == "Added 'new' feature"
