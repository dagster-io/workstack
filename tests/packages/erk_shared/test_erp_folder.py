"""Tests for erp_folder utilities.

Layer 3: Pure unit tests (zero dependencies).

These tests verify the erp_folder module functions work correctly with
basic filesystem operations. No fakes or mocks needed.
"""

import json
from pathlib import Path

import pytest


def test_create_erp_folder_success(tmp_path: Path) -> None:
    """Test creating .erp/ folder with all required files."""
    from erk_shared.erp_folder import create_erp_folder

    plan_content = "# Test Plan\n\n1. First step\n2. Second step"
    issue_number = 123
    issue_url = "https://github.com/owner/repo/issues/123"
    issue_title = "Test Issue"

    erp_folder = create_erp_folder(
        plan_content=plan_content,
        issue_number=issue_number,
        issue_url=issue_url,
        issue_title=issue_title,
        repo_root=tmp_path,
    )

    # Verify folder was created
    assert erp_folder == tmp_path / ".erp"
    assert erp_folder.exists()
    assert erp_folder.is_dir()

    # Verify plan.md exists with correct content
    plan_file = erp_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify issue.json exists with correct structure
    issue_file = erp_folder / "issue.json"
    assert issue_file.exists()
    issue_data = json.loads(issue_file.read_text(encoding="utf-8"))
    assert issue_data["number"] == issue_number
    assert issue_data["url"] == issue_url
    assert issue_data["title"] == issue_title

    # Verify progress.md exists with checkboxes
    progress_file = erp_folder / "progress.md"
    assert progress_file.exists()
    progress_content = progress_file.read_text(encoding="utf-8")
    assert "---" in progress_content  # Front matter
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 2" in progress_content
    assert "- [ ] 1. First step" in progress_content
    assert "- [ ] 2. Second step" in progress_content

    # Verify README.md exists
    readme_file = erp_folder / "README.md"
    assert readme_file.exists()
    readme_content = readme_file.read_text(encoding="utf-8")
    assert "Erk Remote Processing Plan" in readme_content
    assert f"issue #{issue_number}" in readme_content
    assert issue_url in readme_content


def test_create_erp_folder_already_exists(tmp_path: Path) -> None:
    """Test error when .erp/ folder already exists."""
    from erk_shared.erp_folder import create_erp_folder

    # Create .erp/ folder first
    erp_folder = tmp_path / ".erp"
    erp_folder.mkdir()

    # Attempt to create again should raise FileExistsError
    with pytest.raises(FileExistsError, match=".erp/ folder already exists"):
        create_erp_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            issue_title="Test",
            repo_root=tmp_path,
        )


def test_create_erp_folder_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.erp_folder import create_erp_folder

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        create_erp_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            issue_title="Test",
            repo_root=nonexistent_path,
        )


def test_create_erp_folder_repo_root_not_directory(tmp_path: Path) -> None:
    """Test error when repo_root is a file, not a directory."""
    from erk_shared.erp_folder import create_erp_folder

    # Create a file, not a directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="Repository root is not a directory"):
        create_erp_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            issue_title="Test",
            repo_root=file_path,
        )


def test_remove_erp_folder_success(tmp_path: Path) -> None:
    """Test removing .erp/ folder."""
    from erk_shared.erp_folder import create_erp_folder, remove_erp_folder

    # Create .erp/ folder first
    create_erp_folder(
        plan_content="# Test\n\n1. Step one",
        issue_number=123,
        issue_url="https://github.com/owner/repo/issues/123",
        issue_title="Test",
        repo_root=tmp_path,
    )

    erp_folder = tmp_path / ".erp"
    assert erp_folder.exists()

    # Remove it
    remove_erp_folder(tmp_path)

    # Verify it's gone
    assert not erp_folder.exists()


def test_remove_erp_folder_not_exists(tmp_path: Path) -> None:
    """Test error when .erp/ folder doesn't exist."""
    from erk_shared.erp_folder import remove_erp_folder

    with pytest.raises(FileNotFoundError, match=".erp/ folder does not exist"):
        remove_erp_folder(tmp_path)


def test_remove_erp_folder_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.erp_folder import remove_erp_folder

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        remove_erp_folder(nonexistent_path)


def test_erp_folder_exists_true(tmp_path: Path) -> None:
    """Test erp_folder_exists returns True when folder exists."""
    from erk_shared.erp_folder import create_erp_folder, erp_folder_exists

    # Create .erp/ folder
    create_erp_folder(
        plan_content="# Test\n\n1. Step one",
        issue_number=123,
        issue_url="https://github.com/owner/repo/issues/123",
        issue_title="Test",
        repo_root=tmp_path,
    )

    assert erp_folder_exists(tmp_path) is True


def test_erp_folder_exists_false(tmp_path: Path) -> None:
    """Test erp_folder_exists returns False when folder doesn't exist."""
    from erk_shared.erp_folder import erp_folder_exists

    assert erp_folder_exists(tmp_path) is False


def test_erp_folder_exists_repo_root_not_exists(tmp_path: Path) -> None:
    """Test erp_folder_exists returns False when repo_root doesn't exist."""
    from erk_shared.erp_folder import erp_folder_exists

    nonexistent_path = tmp_path / "nonexistent"

    assert erp_folder_exists(nonexistent_path) is False


def test_erp_folder_plan_content_preservation(tmp_path: Path) -> None:
    """Test that plan content is preserved exactly as provided."""
    from erk_shared.erp_folder import create_erp_folder

    # Plan with special characters and formatting
    plan_content = """# Implementation Plan

## Overview
This plan contains **markdown** formatting and `code blocks`.

### Steps
1. First step with `inline code`
2. Second step with special chars: $, &, *, ()

```python
def example():
    return "code block"
```

> Note: blockquote text
"""

    create_erp_folder(
        plan_content=plan_content,
        issue_number=456,
        issue_url="https://github.com/owner/repo/issues/456",
        issue_title="Special chars test",
        repo_root=tmp_path,
    )

    plan_file = tmp_path / ".erp" / "plan.md"
    saved_content = plan_file.read_text(encoding="utf-8")

    # Content should be preserved exactly
    assert saved_content == plan_content


def test_erp_folder_progress_generation(tmp_path: Path) -> None:
    """Test progress.md generation from plan steps."""
    from erk_shared.erp_folder import create_erp_folder

    plan_content = """# Test Plan

1. First step
2. Second step
3. Third step
"""

    create_erp_folder(
        plan_content=plan_content,
        issue_number=789,
        issue_url="https://github.com/owner/repo/issues/789",
        issue_title="Progress test",
        repo_root=tmp_path,
    )

    progress_file = tmp_path / ".erp" / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify front matter
    assert "---" in progress_content
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 3" in progress_content

    # Verify all steps have checkboxes
    assert "- [ ] 1. First step" in progress_content
    assert "- [ ] 2. Second step" in progress_content
    assert "- [ ] 3. Third step" in progress_content
