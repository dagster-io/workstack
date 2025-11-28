"""Integration tests for session-get-plan kit CLI command.

Tests full workflow with realistic session JSONL structure.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.data.kits.erk.kit_cli_commands.erk.session_get_plan import session_get_plan


def test_session_get_plan_with_realistic_session(tmp_path: Path, monkeypatch) -> None:
    """Test full workflow with realistic session JSONL structure."""
    # Setup: Create realistic session structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "erk-session-abc"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "abc-123-def.jsonl"

    # Create realistic session log with multiple entries
    session_entries = [
        {
            "type": "user",
            "message": {
                "content": "Can you help me create a plan?",
                "timestamp": 1234567890
            }
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll create a plan for you."}
                ]
            }
        },
        {
            "type": "user",
            "message": {
                "content": "Tool result: cat > ~/.claude/plans/ethereal-plotting-sunbeam.md\n# Plan\nImplementation details..."
            }
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Plan created successfully."}
                ]
            }
        }
    ]

    session_content = "\n".join(json.dumps(entry) for entry in session_entries)
    session_file.write_text(session_content, encoding="utf-8")

    # Create the plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "ethereal-plotting-sunbeam.md"
    plan_file.write_text("# Implementation Plan\n\nDetails here...", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute: Run CLI command
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "abc-123-def"])

    # Assert: Verify success
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == "abc-123-def"
    assert output["plan_filename"] == "ethereal-plotting-sunbeam.md"
    assert str(plan_file) in output["plan_path"]


def test_session_get_plan_from_environment_auto_detect(tmp_path: Path, monkeypatch) -> None:
    """Test auto-detection from SESSION_CONTEXT environment variable."""
    # Setup: Create session structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "project-env"
    project_dir.mkdir(parents=True)

    session_id = "a02a1cae-b32a-41c1-a107-945ff5828724"
    session_file = project_dir / f"{session_id}.jsonl"

    session_entries = [
        {
            "type": "user",
            "message": {
                "content": "plans/feature-implementation.md"
            }
        }
    ]

    session_content = "\n".join(json.dumps(entry) for entry in session_entries)
    session_file.write_text(session_content, encoding="utf-8")

    # Create plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "feature-implementation.md"
    plan_file.write_text("# Feature Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SESSION_CONTEXT", f"session_id={session_id}")

    # Execute: Run without --session-id flag
    runner = CliRunner()
    result = runner.invoke(session_get_plan, [])

    # Assert: Should auto-detect from environment
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == session_id
    assert output["plan_filename"] == "feature-implementation.md"


def test_session_get_plan_with_multiple_plans_in_session(tmp_path: Path, monkeypatch) -> None:
    """Test returns most recent plan when session has multiple plans."""
    # Setup: Create session with multiple plan writes
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "multi-plan-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "multi-123.jsonl"

    session_entries = [
        {
            "type": "user",
            "message": {"content": "plans/first-draft-plan.md"}
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "First plan created"}]}
        },
        {
            "type": "user",
            "message": {"content": "plans/second-revision-plan.md"}
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Second plan created"}]}
        },
        {
            "type": "user",
            "message": {"content": "plans/final-implementation-plan.md"}
        }
    ]

    session_content = "\n".join(json.dumps(entry) for entry in session_entries)
    session_file.write_text(session_content, encoding="utf-8")

    # Create the final plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "final-implementation-plan.md").write_text("# Final Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "multi-123"])

    # Assert: Should return last plan
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_filename"] == "final-implementation-plan.md"


def test_session_get_plan_with_agent_logs_excluded(tmp_path: Path, monkeypatch) -> None:
    """Test that agent log plans are excluded from results."""
    # Setup: Create session with agent logs and real plans
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "agent-test-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "agent-test.jsonl"

    session_entries = [
        {
            "type": "user",
            "message": {"content": "plans/agent-internal-log.md"}
        },
        {
            "type": "user",
            "message": {"content": "plans/agent-debug-output.md"}
        },
        {
            "type": "user",
            "message": {"content": "plans/user-feature-plan.md"}
        }
    ]

    session_content = "\n".join(json.dumps(entry) for entry in session_entries)
    session_file.write_text(session_content, encoding="utf-8")

    # Create the user plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "user-feature-plan.md").write_text("# User Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "agent-test"])

    # Assert: Should exclude agent- prefixed plans
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_filename"] == "user-feature-plan.md"
    assert "agent-" not in output["plan_filename"]


def test_session_get_plan_with_malformed_json_handling(tmp_path: Path, monkeypatch) -> None:
    """Test graceful handling of malformed JSON in session log."""
    # Setup: Create session with some invalid JSON lines
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "malformed-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "malformed-123.jsonl"

    lines = [
        "{ this is not valid json }",
        json.dumps({"type": "user", "message": {"content": "some text"}}),
        "another invalid line",
        "",
        json.dumps({"type": "user", "message": {"content": "plans/valid-plan.md"}}),
        "{ incomplete"
    ]

    session_file.write_text("\n".join(lines), encoding="utf-8")

    # Create plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "valid-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "malformed-123"])

    # Assert: Should find valid plan despite malformed lines
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_filename"] == "valid-plan.md"


def test_session_get_plan_text_output_for_scripting(tmp_path: Path, monkeypatch) -> None:
    """Test --text flag for shell scripting integration."""
    # Setup
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "script-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "script-123.jsonl"
    session_file.write_text(
        json.dumps({"type": "user", "message": {"content": "plans/automation-script.md"}}),
        encoding="utf-8"
    )

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "automation-script.md").write_text("# Script", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute: Use --text flag
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "script-123", "--text"])

    # Assert: Should output plain filename (no JSON)
    assert result.exit_code == 0
    assert result.output.strip() == "automation-script.md"
    # Should NOT be JSON
    assert "{" not in result.output
    assert "}" not in result.output


def test_session_get_plan_bare_uuid_in_environment(tmp_path: Path, monkeypatch) -> None:
    """Test auto-detection with bare UUID in SESSION_CONTEXT."""
    # Setup
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "bare-uuid-project"
    project_dir.mkdir(parents=True)

    session_id = "b12c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"
    session_file = project_dir / f"{session_id}.jsonl"
    session_file.write_text(
        json.dumps({"type": "user", "message": {"content": "plans/uuid-test-plan.md"}}),
        encoding="utf-8"
    )

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "uuid-test-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Set bare UUID (no "session_id=" prefix)
    monkeypatch.setenv("SESSION_CONTEXT", session_id)

    # Execute
    runner = CliRunner()
    result = runner.invoke(session_get_plan, [])

    # Assert: Should auto-detect bare UUID
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == session_id
    assert output["plan_filename"] == "uuid-test-plan.md"


def test_session_get_plan_across_multiple_project_dirs(tmp_path: Path, monkeypatch) -> None:
    """Test finding session file when multiple project directories exist."""
    # Setup: Create multiple project directories
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Project 1
    (projects_dir / "project-1").mkdir()
    (projects_dir / "project-1" / "session-a.jsonl").write_text("{}", encoding="utf-8")

    # Project 2 (target)
    project_2 = projects_dir / "project-2"
    project_2.mkdir()
    target_session = project_2 / "target-session.jsonl"
    target_session.write_text(
        json.dumps({"type": "user", "message": {"content": "plans/target-plan.md"}}),
        encoding="utf-8"
    )

    # Project 3
    (projects_dir / "project-3").mkdir()
    (projects_dir / "project-3" / "session-c.jsonl").write_text("{}", encoding="utf-8")

    # Create plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "target-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Execute
    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "target-session"])

    # Assert: Should find the correct session across projects
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_filename"] == "target-plan.md"
