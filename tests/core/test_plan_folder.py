"""Tests for plan folder management utilities."""

from pathlib import Path

import pytest

from erk.core.plan_folder import (
    copy_plan_to_submission,
    create_plan_folder,
    extract_steps_from_plan,
    get_plan_path,
    get_progress_path,
    get_submission_path,
    parse_progress_frontmatter,
    remove_submission_folder,
    update_progress,
    update_progress_frontmatter,
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


def test_create_plan_folder_generates_frontmatter(tmp_path: Path) -> None:
    """Test that creating a plan folder generates YAML front matter in progress.md."""
    plan_content = """# Test Plan

1. First step
2. Second step
3. Third step
"""
    plan_folder = create_plan_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify front matter exists
    assert progress_content.startswith("---\n")
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 3" in progress_content
    assert "---\n\n" in progress_content


def test_parse_progress_frontmatter_valid(tmp_path: Path) -> None:
    """Test parsing valid YAML front matter."""
    content = """---
completed_steps: 3
total_steps: 10
---

# Progress Tracking

- [x] 1. Step one
- [x] 2. Step two
- [x] 3. Step three
- [ ] 4. Step four
"""
    result = parse_progress_frontmatter(content)

    assert result is not None
    assert result["completed_steps"] == 3
    assert result["total_steps"] == 10


def test_parse_progress_frontmatter_missing(tmp_path: Path) -> None:
    """Test parsing progress file without front matter."""
    content = """# Progress Tracking

- [ ] 1. Step one
- [ ] 2. Step two
"""
    result = parse_progress_frontmatter(content)

    assert result is None


def test_parse_progress_frontmatter_invalid_yaml(tmp_path: Path) -> None:
    """Test parsing progress file with invalid YAML."""
    content = """---
completed_steps: [invalid yaml
total_steps: 10
---

# Progress Tracking
"""
    result = parse_progress_frontmatter(content)

    assert result is None


def test_parse_progress_frontmatter_missing_fields(tmp_path: Path) -> None:
    """Test parsing front matter with missing required fields."""
    content = """---
completed_steps: 3
---

# Progress Tracking
"""
    result = parse_progress_frontmatter(content)

    assert result is None


def test_update_progress_frontmatter_replaces_existing(tmp_path: Path) -> None:
    """Test updating existing front matter preserves checkbox content."""
    plan_content = "# Test\n\n1. Step one\n2. Step two"
    create_plan_folder(tmp_path, plan_content)

    # Manually mark first checkbox as completed
    progress_file = tmp_path / ".plan" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")
    content = content.replace("- [ ] 1. Step one", "- [x] 1. Step one")
    progress_file.write_text(content, encoding="utf-8")

    # Update front matter to reflect 1/2 completed
    update_progress_frontmatter(tmp_path, 1, 2)

    # Verify front matter updated
    updated_content = progress_file.read_text(encoding="utf-8")
    assert "completed_steps: 1" in updated_content
    assert "total_steps: 2" in updated_content

    # Verify checkboxes preserved
    assert "- [x] 1. Step one" in updated_content
    assert "- [ ] 2. Step two" in updated_content


def test_update_progress_frontmatter_adds_if_missing(tmp_path: Path) -> None:
    """Test adding front matter to file that doesn't have it."""
    # Create progress file without front matter
    plan_folder = tmp_path / ".plan"
    plan_folder.mkdir()
    progress_file = plan_folder / "progress.md"
    progress_file.write_text(
        """# Progress Tracking

- [x] 1. Step one
- [ ] 2. Step two
""",
        encoding="utf-8",
    )

    # Add front matter
    update_progress_frontmatter(tmp_path, 1, 2)

    # Verify front matter added
    updated_content = progress_file.read_text(encoding="utf-8")
    assert updated_content.startswith("---\n")
    assert "completed_steps: 1" in updated_content
    assert "total_steps: 2" in updated_content

    # Verify checkboxes preserved
    assert "- [x] 1. Step one" in updated_content
    assert "- [ ] 2. Step two" in updated_content


def test_update_progress_frontmatter_no_file(tmp_path: Path) -> None:
    """Test updating front matter when file doesn't exist does nothing."""
    # Should not raise error
    update_progress_frontmatter(tmp_path, 1, 2)


def test_copy_plan_to_submission_success(tmp_path: Path) -> None:
    """Test copying .plan/ folder to .submission/ folder."""
    # Create .plan/ folder with content
    plan_content = "# Test Plan\n\n1. Step one\n2. Step two"
    plan_folder = create_plan_folder(tmp_path, plan_content)

    # Verify .plan/ exists
    assert plan_folder.exists()
    assert (plan_folder / "plan.md").exists()
    assert (plan_folder / "progress.md").exists()

    # Copy to .submission/
    submission_folder = copy_plan_to_submission(tmp_path)

    # Verify .submission/ exists and has same content
    assert submission_folder.exists()
    assert submission_folder == tmp_path / ".submission"
    assert (submission_folder / "plan.md").exists()
    assert (submission_folder / "progress.md").exists()

    # Verify content matches
    assert (submission_folder / "plan.md").read_text(encoding="utf-8") == plan_content
    assert (submission_folder / "progress.md").exists()


def test_copy_plan_to_submission_no_plan(tmp_path: Path) -> None:
    """Test copy_plan_to_submission raises error when no .plan/ folder exists."""
    # No .plan/ folder created
    with pytest.raises(FileNotFoundError, match="No .plan/ folder found"):
        copy_plan_to_submission(tmp_path)


def test_copy_plan_to_submission_already_exists(tmp_path: Path) -> None:
    """Test copy_plan_to_submission replaces existing .submission/ (idempotent)."""
    # Create .plan/ folder
    plan_content = "# Test Plan\n\n1. Step"
    create_plan_folder(tmp_path, plan_content)

    # Create .submission/ folder with old content
    submission_folder = tmp_path / ".submission"
    submission_folder.mkdir()
    old_file = submission_folder / "old.txt"
    old_file.write_text("old content", encoding="utf-8")

    # Copy should replace existing folder (idempotent)
    result_folder = copy_plan_to_submission(tmp_path)

    # Verify .submission/ was replaced with .plan/ contents
    assert result_folder.exists()
    assert (submission_folder / "plan.md").exists()
    assert (submission_folder / "progress.md").exists()
    assert not old_file.exists()  # Old content removed


def test_get_submission_path_exists(tmp_path: Path) -> None:
    """Test get_submission_path returns path when .submission/ exists."""
    # Create .plan/ and copy to .submission/
    plan_content = "# Test Plan\n\n1. Step"
    create_plan_folder(tmp_path, plan_content)
    copy_plan_to_submission(tmp_path)

    # Get submission path
    submission_path = get_submission_path(tmp_path)

    assert submission_path is not None
    assert submission_path == tmp_path / ".submission"
    assert submission_path.exists()


def test_get_submission_path_not_exists(tmp_path: Path) -> None:
    """Test get_submission_path returns None when .submission/ doesn't exist."""
    submission_path = get_submission_path(tmp_path)
    assert submission_path is None


def test_remove_submission_folder_exists(tmp_path: Path) -> None:
    """Test remove_submission_folder removes .submission/ folder."""
    # Create .plan/ and copy to .submission/
    plan_content = "# Test Plan\n\n1. Step"
    create_plan_folder(tmp_path, plan_content)
    copy_plan_to_submission(tmp_path)

    # Verify .submission/ exists
    submission_folder = tmp_path / ".submission"
    assert submission_folder.exists()

    # Remove .submission/
    remove_submission_folder(tmp_path)

    # Verify .submission/ is gone
    assert not submission_folder.exists()

    # Verify .plan/ still exists
    plan_folder = tmp_path / ".plan"
    assert plan_folder.exists()


def test_remove_submission_folder_not_exists(tmp_path: Path) -> None:
    """Test remove_submission_folder does nothing when .submission/ doesn't exist."""
    # Should not raise error
    remove_submission_folder(tmp_path)

    # Verify still doesn't exist
    submission_folder = tmp_path / ".submission"
    assert not submission_folder.exists()
