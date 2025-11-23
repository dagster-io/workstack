"""Integration tests for implement-plan kit CLI command.

Tests the complete validation workflow for .impl/ folder structure and issue tracking.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.implement_plan import (
    implement_plan,
)


def test_implement_plan_validates_complete_issue_json(tmp_path: Path, monkeypatch) -> None:
    """Test that implement-plan validates issue.json has all required fields."""
    # Create .impl/ folder structure
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing\n2. Do other thing")

    # Create progress.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 2\n---\n\n- [ ] 1. Do thing\n- [ ] 2. Do other thing"
    )

    # Write COMPLETE format issue.json
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 123,
                "issue_url": "https://github.com/org/repo/issues/123",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        )
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify success
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is True
    assert data["plan_length"] > 0


def test_implement_plan_handles_incomplete_issue_json(tmp_path: Path, monkeypatch) -> None:
    """Test that incomplete issue.json is detected and tracking disabled."""
    # Create .impl/ folder structure
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing")

    # Create progress.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] 1. Do thing"
    )

    # Write SIMPLE format issue.json (missing timestamps)
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 123,
                "issue_url": "https://github.com/org/repo/issues/123",
            }
        )
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify success but tracking disabled
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is False  # Tracking disabled due to incomplete format


def test_implement_plan_handles_missing_issue_json(tmp_path: Path, monkeypatch) -> None:
    """Test that missing issue.json is handled gracefully."""
    # Create .impl/ folder structure WITHOUT issue.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing")

    # Create progress.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] 1. Do thing"
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify success without tracking
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is False


def test_implement_plan_errors_on_missing_plan(tmp_path: Path, monkeypatch) -> None:
    """Test error when plan.md is missing."""
    # Create .impl/ folder WITHOUT plan.md
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create only progress.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] 1. Do thing"
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify error
    assert result.exit_code == 1
    assert "No plan.md found" in result.output


def test_implement_plan_errors_on_missing_progress(tmp_path: Path, monkeypatch) -> None:
    """Test error when progress.md is missing."""
    # Create .impl/ folder WITHOUT progress.md
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create only plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing")

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify error
    assert result.exit_code == 1
    assert "No progress.md found" in result.output


def test_implement_plan_errors_on_missing_impl_folder(tmp_path: Path, monkeypatch) -> None:
    """Test error when .impl/ folder doesn't exist."""
    # Don't create .impl/ folder at all
    monkeypatch.chdir(tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(implement_plan, ["--dry-run"])

    # Verify error
    assert result.exit_code == 1
    assert "No .impl/ folder found" in result.output


def test_implement_plan_normal_mode_with_tracking(tmp_path: Path, monkeypatch) -> None:
    """Test normal mode outputs instructions with tracking enabled."""
    # Create .impl/ folder structure with complete issue.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing")

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] 1. Do thing"
    )

    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 456,
                "issue_url": "https://github.com/org/repo/issues/456",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        )
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command in normal mode (no --dry-run)
    runner = CliRunner()
    result = runner.invoke(implement_plan, [])

    # Verify success and instructions output
    assert result.exit_code == 0
    assert "Plan loaded from .impl/plan.md" in result.output
    assert "GitHub tracking: ENABLED (issue #456)" in result.output
    assert "/erk:implement-plan" in result.output


def test_implement_plan_normal_mode_without_tracking(tmp_path: Path, monkeypatch) -> None:
    """Test normal mode outputs instructions with tracking disabled."""
    # Create .impl/ folder structure WITHOUT issue.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n## Steps\n1. Do thing")

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] 1. Do thing"
    )

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    # Run command in normal mode
    runner = CliRunner()
    result = runner.invoke(implement_plan, [])

    # Verify success and instructions output
    assert result.exit_code == 0
    assert "Plan loaded from .impl/plan.md" in result.output
    assert "GitHub tracking: DISABLED (no issue.json)" in result.output
    assert "/erk:implement-plan" in result.output
