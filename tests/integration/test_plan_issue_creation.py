"""Integration tests for plan issue creation workflow.

Tests the full workflow from plan content to wrapped metadata block.
Uses subprocess to call the actual kit CLI command.
"""

import subprocess


def test_wrap_plan_command_produces_valid_output() -> None:
    """Test wrap-plan-in-metadata-block command produces correct format."""
    plan_content = """# Test Implementation Plan

## Overview
This is a test plan for verification.

## Implementation Steps
1. First step
2. Second step
3. Third step

## Success Criteria
- All tests pass
- Code follows standards"""

    # Call the actual kit CLI command
    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify output structure
    assert "This issue contains an implementation plan:" in output
    assert "<details>" in output
    assert "<summary><code>erk-plan</code></summary>" in output
    assert "</details>" in output

    # Verify plan content is preserved (raw markdown, no YAML fence)
    assert "# Test Implementation Plan" in output
    assert "## Overview" in output
    assert "## Implementation Steps" in output
    assert "1. First step" in output
    assert "2. Second step" in output
    assert "## Success Criteria" in output

    # Verify no 'open' attribute (collapsed by default)
    assert "open" not in output.lower()


def test_wrap_plan_command_handles_empty_input() -> None:
    """Test wrap-plan-in-metadata-block handles empty input gracefully."""
    # Call with empty input
    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input="",
        capture_output=True,
        text=True,
    )

    # Should fail with error
    assert result.returncode != 0
    assert "Error: Empty plan content" in result.stderr


def test_wrap_plan_command_preserves_special_characters() -> None:
    """Test wrap-plan-in-metadata-block preserves special characters."""
    plan_content = """# Plan with Special Characters

- Quotes: "double" and 'single'
- Backticks: `code snippet`
- Symbols: @#$%^&*()
- Unicode: 🔥 ✅ ❌
- Line breaks and spacing

    Indented content"""

    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify all special characters are preserved
    assert '"double"' in output
    assert "'single'" in output
    assert "`code snippet`" in output
    assert "@#$%^&*()" in output
    assert "🔥" in output
    assert "✅" in output
    assert "❌" in output
    assert "Indented content" in output


def test_wrap_plan_command_with_very_long_plan() -> None:
    """Test wrap-plan-in-metadata-block handles large plans."""
    # Create a large plan (simulate a realistic size)
    sections = []
    for i in range(20):
        sections.append(f"## Phase {i + 1}")
        for j in range(10):
            sections.append(f"- Task {i + 1}.{j + 1}: Description of task")

    plan_content = "# Large Implementation Plan\n\n" + "\n".join(sections)

    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify structure is maintained
    assert "This issue contains an implementation plan:" in output
    assert "<details>" in output
    assert "</details>" in output

    # Verify content is complete (check first and last sections)
    assert "## Phase 1" in output
    assert "## Phase 20" in output
    assert "Task 1.1" in output
    assert "Task 20.10" in output
