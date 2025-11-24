"""ERP (Erk Remote Processing) folder utilities for remote queue submission.

This module provides utilities for managing .erp/ folder structures used during
remote queue submission workflow. The .erp/ folder is committed to the branch
and contains the implementation plan, making it visible in the PR immediately.

Unlike .impl/ folders (ephemeral, local, never committed), .erp/ folders are:
- Committed to the branch
- Visible in draft PR immediately
- Removed after implementation completes

Folder structure:
.erp/
├── plan.md          # Full plan content from GitHub issue
├── issue.json       # {"number": 123, "url": "...", "title": "..."}
├── progress.md      # Progress tracking checkboxes
└── README.md        # Explanation that folder is temporary
"""

import json
from pathlib import Path

from erk_shared.impl_folder import extract_steps_from_plan


def create_erp_folder(
    plan_content: str,
    issue_number: int,
    issue_url: str,
    issue_title: str,
    repo_root: Path,
) -> Path:
    """Create .erp/ folder with all required files.

    Args:
        plan_content: Full plan markdown content from GitHub issue
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        issue_title: GitHub issue title
        repo_root: Repository root directory path

    Returns:
        Path to the created .erp/ directory

    Raises:
        FileExistsError: If .erp/ folder already exists
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    # Validate repo_root exists and is a directory (LBYL)
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    erp_folder = repo_root / ".erp"

    # Check if folder already exists (LBYL)
    if erp_folder.exists():
        raise FileExistsError(f".erp/ folder already exists at {erp_folder}")

    # Create .erp/ directory
    erp_folder.mkdir(parents=True, exist_ok=False)

    # Write plan.md
    plan_file = erp_folder / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Write issue.json
    issue_data = {
        "number": issue_number,
        "url": issue_url,
        "title": issue_title,
    }
    issue_file = erp_folder / "issue.json"
    issue_file.write_text(json.dumps(issue_data, indent=2) + "\n", encoding="utf-8")

    # Generate and write progress.md
    steps = extract_steps_from_plan(plan_content)
    progress_content = _generate_progress_content(steps)
    progress_file = erp_folder / "progress.md"
    progress_file.write_text(progress_content, encoding="utf-8")

    # Write README.md
    readme_content = f"""# .erp/ - Erk Remote Processing Plan

This folder contains the implementation plan for this branch.

**Status:** Queued for remote implementation

**Source:** GitHub issue #{issue_number}
{issue_url}

**This folder is temporary** and will be automatically removed after implementation completes.
"""
    readme_file = erp_folder / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")

    return erp_folder


def remove_erp_folder(repo_root: Path) -> None:
    """Remove .erp/ folder and all contents.

    Args:
        repo_root: Repository root directory path

    Raises:
        FileNotFoundError: If .erp/ folder doesn't exist
        ValueError: If repo_root doesn't exist or isn't a directory
    """
    # Validate repo_root exists and is a directory (LBYL)
    if not repo_root.exists():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    erp_folder = repo_root / ".erp"

    # Check if folder exists (LBYL)
    if not erp_folder.exists():
        raise FileNotFoundError(f".erp/ folder does not exist at {erp_folder}")

    # Import shutil for rmtree
    import shutil

    shutil.rmtree(erp_folder)


def erp_folder_exists(repo_root: Path) -> bool:
    """Check if .erp/ folder exists in repo root.

    Args:
        repo_root: Repository root directory path

    Returns:
        True if .erp/ folder exists, False otherwise
    """
    # Check if repo_root exists first (LBYL)
    if not repo_root.exists():
        return False

    erp_folder = repo_root / ".erp"
    return erp_folder.exists()


def _generate_progress_content(steps: list[str]) -> str:
    """Generate progress.md content with YAML front matter and checkboxes.

    Args:
        steps: List of step descriptions

    Returns:
        Formatted progress markdown with front matter and unchecked boxes
    """
    if not steps:
        return "# Progress Tracking\n\nNo steps detected in plan.\n"

    # Generate YAML front matter
    total_steps = len(steps)
    front_matter = f"---\ncompleted_steps: 0\ntotal_steps: {total_steps}\n---\n\n"

    lines = [front_matter + "# Progress Tracking\n"]

    for step in steps:
        # Create checkbox: - [ ] Step description
        lines.append(f"- [ ] {step}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)
