"""Tests for plan folder management utilities."""

from pathlib import Path

import pytest

from erk.core.plan_folder import (
    create_plan_folder,
    extract_steps_from_plan,
    get_plan_path,
    get_progress_path,
    update_progress,
)


def test_create_plan_folder_basic(tmp_path: Path) -> None:
    """Test creating a plan folder with basic plan content."""
    plan_content = """# Implementation Plan: Test Feature

## Objective
Build a test feature.

## Implementation Steps

1. Create module
2. Add tests
3. Update documentation
"""

    plan_folder = create_plan_folder(tmp_path, plan_content)

    # Verify folder structure
    assert plan_folder.exists()
    assert plan_folder == tmp_path / ".plan"

    # Verify plan.md exists and has correct content
    plan_file = plan_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify progress.md exists and has checkboxes
    progress_file = plan_folder / "progress.md"
    assert progress_file.exists()
    progress_content = progress_file.read_text(encoding="utf-8")
    assert "- [ ] 1. Create module" in progress_content
    assert "- [ ] 2. Add tests" in progress_content
    assert "- [ ] 3. Update documentation" in progress_content


def test_create_plan_folder_already_exists(tmp_path: Path) -> None:
    """Test that creating a plan folder when one exists raises error."""
    plan_content = "# Test Plan\n\n1. Step one"

    # Create first time - should succeed
    create_plan_folder(tmp_path, plan_content)

    # Try to create again - should raise
    with pytest.raises(FileExistsError, match="Plan folder already exists"):
        create_plan_folder(tmp_path, plan_content)


def test_create_plan_folder_with_nested_steps(tmp_path: Path) -> None:
    """Test creating plan folder with nested step numbering."""
    plan_content = """# Complex Plan

## Phase 1

1. Main step one
1.1. Substep one
1.2. Substep two

2. Main step two
2.1. Substep one
2.2. Substep two
2.3. Substep three
"""

    plan_folder = create_plan_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify all steps are in progress.md
    assert "- [ ] 1. Main step one" in progress_content
    assert "- [ ] 1.1. Substep one" in progress_content
    assert "- [ ] 1.2. Substep two" in progress_content
    assert "- [ ] 2. Main step two" in progress_content
    assert "- [ ] 2.1. Substep one" in progress_content
    assert "- [ ] 2.2. Substep two" in progress_content
    assert "- [ ] 2.3. Substep three" in progress_content


def test_create_plan_folder_empty_plan(tmp_path: Path) -> None:
    """Test creating plan folder with empty or no-steps plan."""
    plan_content = """# Empty Plan

This plan has no numbered steps.
Just some text.
"""

    plan_folder = create_plan_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Should create progress.md with message about no steps
    assert progress_file.exists()
    assert "No steps detected" in progress_content


def test_get_plan_path_exists(tmp_path: Path) -> None:
    """Test getting plan path when it exists."""
    plan_content = "# Test\n\n1. Step"
    create_plan_folder(tmp_path, plan_content)

    plan_path = get_plan_path(tmp_path)
    assert plan_path is not None
    assert plan_path == tmp_path / ".plan" / "plan.md"
    assert plan_path.exists()


def test_get_plan_path_not_exists(tmp_path: Path) -> None:
    """Test getting plan path when it doesn't exist."""
    plan_path = get_plan_path(tmp_path)
    assert plan_path is None


def test_get_progress_path_exists(tmp_path: Path) -> None:
    """Test getting progress path when it exists."""
    plan_content = "# Test\n\n1. Step"
    create_plan_folder(tmp_path, plan_content)

    progress_path = get_progress_path(tmp_path)
    assert progress_path is not None
    assert progress_path == tmp_path / ".plan" / "progress.md"
    assert progress_path.exists()


def test_get_progress_path_not_exists(tmp_path: Path) -> None:
    """Test getting progress path when it doesn't exist."""
    progress_path = get_progress_path(tmp_path)
    assert progress_path is None


def test_update_progress(tmp_path: Path) -> None:
    """Test updating progress.md content."""
    plan_content = "# Test\n\n1. Step one\n2. Step two"
    create_plan_folder(tmp_path, plan_content)

    # Update progress with completed first step
    new_progress = """# Progress Tracking

- [x] 1. Step one
- [ ] 2. Step two
"""
    update_progress(tmp_path, new_progress)

    # Verify update
    progress_file = tmp_path / ".plan" / "progress.md"
    assert progress_file.read_text(encoding="utf-8") == new_progress


def test_extract_steps_numbered_with_period(tmp_path: Path) -> None:
    """Test extracting steps with '1.' format."""
    plan = """# Plan

1. First step
2. Second step
3. Third step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3
    assert "1. First step" in steps
    assert "2. Second step" in steps
    assert "3. Third step" in steps


def test_extract_steps_numbered_with_paren(tmp_path: Path) -> None:
    """Test extracting steps with '1)' format."""
    plan = """# Plan

1) First step
2) Second step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "1) First step" in steps
    assert "2) Second step" in steps


def test_extract_steps_with_step_word(tmp_path: Path) -> None:
    """Test extracting steps with 'Step X:' format."""
    plan = """# Plan

Step 1: First step
Step 2: Second step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "Step 1: First step" in steps
    assert "Step 2: Second step" in steps


def test_extract_steps_nested_numbering(tmp_path: Path) -> None:
    """Test extracting steps with nested numbering."""
    plan = """# Plan

1. Main step
1.1. Substep A
1.2. Substep B
2. Another main step
2.1. Substep C
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 5
    assert "1. Main step" in steps
    assert "1.1. Substep A" in steps
    assert "1.2. Substep B" in steps
    assert "2. Another main step" in steps
    assert "2.1. Substep C" in steps


def test_extract_steps_mixed_formats(tmp_path: Path) -> None:
    """Test extracting steps from plan with mixed formats."""
    plan = """# Plan

1. First format
2) Second format
Step 3: Third format
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3


def test_extract_steps_ignores_non_steps(tmp_path: Path) -> None:
    """Test that extraction ignores non-step content."""
    plan = """# Plan

This is intro text.

1. Actual step
2. Another step

Some more text that isn't a step.
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "1. Actual step" in steps
    assert "2. Another step" in steps


def test_extract_steps_empty_plan(tmp_path: Path) -> None:
    """Test extracting steps from plan with no steps."""
    plan = """# Plan

Just text, no steps.
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 0


def test_extract_steps_indented_steps(tmp_path: Path) -> None:
    """Test extracting indented steps."""
    plan = """# Plan

   1. Indented step
     2. More indented
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert any("1. Indented step" in s for s in steps)
    assert any("2. More indented" in s for s in steps)


def test_extract_steps_with_special_characters(tmp_path: Path) -> None:
    """Test extracting steps with special characters in descriptions."""
    plan = """# Plan

1. Step with **bold** and *italic*
2. Step with `code` and [link](url)
3. Step with emoji 🎉
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3
    # Steps should preserve the full line including special characters
    assert any("**bold**" in s for s in steps)
    assert any("`code`" in s for s in steps)
    assert any("🎉" in s for s in steps)
