"""Unit tests for post_progress_comment kit CLI command.

Tests progress comment posting with structured YAML in collapsible details sections.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import yaml
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment import (
    post_progress_comment,
)
from erk.core.github.issues import FakeGitHubIssues

# ============================================================================
# 1. Success Case Tests (2 tests)
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

    # Mock RealGitHubIssues with FakeGitHubIssues
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
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Phase 1: Create abstraction"],
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
    comment_number, comment_body = fake_issues.added_comments[0]
    assert comment_number == 123

    # Verify comment format
    assert "✓ Step 3/5 completed" in comment_body
    assert "<details>" in comment_body
    assert "<summary><code>erk-implementation-status</code></summary>" in comment_body
    assert "```yaml" in comment_body

    # Parse and verify YAML
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)

    assert parsed_yaml["status"] == "in_progress"
    assert parsed_yaml["completed_steps"] == 3
    assert parsed_yaml["total_steps"] == 5
    assert parsed_yaml["percentage"] == 60
    assert parsed_yaml["step_description"] == "Phase 1: Create abstraction"
    assert "timestamp" in parsed_yaml


def test_success_case_100_percent(tmp_path: Path, monkeypatch) -> None:
    """Test progress comment with 100% completion (not completion command)."""
    # Setup temp directory structure
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

    # Create progress.md with 100% completion
    progress_content = """---
completed_steps: 5
total_steps: 5
---

# Progress
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    # Mock subprocess.run
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Mock RealGitHubIssues
    fake_issues = FakeGitHubIssues(issues={456: MagicMock(number=456)})
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Final step"],
    )

    # Should succeed (not error even at 100%)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["progress"] == "5/5 (100%)"


# ============================================================================
# 2. Error Case Tests (5 tests)
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
        post_progress_comment,
        ["--step-description", "Test"],
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
        post_progress_comment,
        ["--step-description", "Test"],
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
        post_progress_comment,
        ["--step-description", "Test"],
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid_progress_format"


def test_not_in_git_repo(tmp_path: Path, monkeypatch) -> None:
    """Test error when not in a git repository."""

    # Mock subprocess.run to fail
    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "not_in_repo"


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

    # Create progress.md
    progress_content = """---
completed_steps: 2
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

    # Mock RealGitHubIssues to raise error (issue not found)
    fake_issues = FakeGitHubIssues(issues={})  # Empty - issue 999 doesn't exist
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    # Verify exit code 0
    assert result.exit_code == 0

    # Verify error JSON
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "github_api_failed"
    assert "999" in output["message"]


# ============================================================================
# 3. Edge Case Tests (6 tests)
# ============================================================================


def test_edge_case_zero_percent(tmp_path: Path, monkeypatch) -> None:
    """Test with 0% progress."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 100,
        "issue_url": "https://github.com/owner/repo/issues/100",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 0
total_steps: 5
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={100: MagicMock(number=100)})
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Starting"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["progress"] == "0/5 (0%)"


def test_edge_case_50_percent(tmp_path: Path, monkeypatch) -> None:
    """Test with 50% progress (3/6 steps)."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 200,
        "issue_url": "https://github.com/owner/repo/issues/200",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 3
total_steps: 6
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={200: MagicMock(number=200)})
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Midway"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["progress"] == "3/6 (50%)"


def test_edge_case_unicode_in_description(tmp_path: Path, monkeypatch) -> None:
    """Test with Unicode characters in step description."""
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
completed_steps: 1
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
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "✓ Phase 1: Create façade"],
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
    assert parsed_yaml["step_description"] == "✓ Phase 1: Create façade"


def test_edge_case_colon_in_description(tmp_path: Path, monkeypatch) -> None:
    """Test YAML escaping with colon in step description."""
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
completed_steps: 2
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
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Phase 1: Create API"],
    )

    assert result.exit_code == 0

    # Verify YAML is valid and colon is properly escaped
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)
    assert parsed_yaml["step_description"] == "Phase 1: Create API"


def test_edge_case_quotes_in_description(tmp_path: Path, monkeypatch) -> None:
    """Test YAML escaping with quotes in step description."""
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
completed_steps: 1
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
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", 'Fix "broken" feature'],
    )

    assert result.exit_code == 0

    # Verify YAML is valid and quotes are properly escaped
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)
    assert parsed_yaml["step_description"] == 'Fix "broken" feature'


def test_yaml_timestamp_is_iso_format(tmp_path: Path, monkeypatch) -> None:
    """Test that timestamp field is valid ISO format."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = {
        "issue_number": 600,
        "issue_url": "https://github.com/owner/repo/issues/600",
        "created_at": "2025-11-22T10:00:00Z",
        "synced_at": "2025-11-22T10:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_json), encoding="utf-8")

    progress_content = """---
completed_steps: 1
total_steps: 1
---
"""
    (impl_dir / "progress.md").write_text(progress_content, encoding="utf-8")

    def mock_run(*args, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = str(tmp_path)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    fake_issues = FakeGitHubIssues(issues={600: MagicMock(number=600)})
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_progress_comment.RealGitHubIssues",
        lambda: fake_issues,
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_progress_comment,
        ["--step-description", "Test"],
    )

    assert result.exit_code == 0

    # Verify timestamp is valid ISO format
    comment_body = fake_issues.added_comments[0][1]
    yaml_start = comment_body.find("```yaml\n") + len("```yaml\n")
    yaml_end = comment_body.find("\n```", yaml_start)
    yaml_content = comment_body[yaml_start:yaml_end]
    parsed_yaml = yaml.safe_load(yaml_content)

    # Should be able to parse as ISO format (will raise if invalid)
    from datetime import datetime

    datetime.fromisoformat(parsed_yaml["timestamp"])
