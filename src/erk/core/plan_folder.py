"""Plan folder management utilities.

This module handles the .plan/ folder structure:
- plan.md: Immutable implementation plan
- progress.md: Mutable progress tracking with step checkboxes
"""

import re
from pathlib import Path


def create_plan_folder(worktree_path: Path, plan_content: str) -> Path:
    """Create .plan/ folder with plan.md and progress.md files.

    Args:
        worktree_path: Path to the worktree directory
        plan_content: Content for plan.md file

    Returns:
        Path to the created .plan/ directory

    Raises:
        FileExistsError: If .plan/ directory already exists
    """
    plan_folder = worktree_path / ".plan"

    if plan_folder.exists():
        raise FileExistsError(f"Plan folder already exists at {plan_folder}")

    # Create .plan/ directory
    plan_folder.mkdir(parents=True, exist_ok=False)

    # Write immutable plan.md
    plan_file = plan_folder / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Extract steps and generate progress.md
    steps = extract_steps_from_plan(plan_content)
    progress_content = _generate_progress_content(steps)

    progress_file = plan_folder / "progress.md"
    progress_file.write_text(progress_content, encoding="utf-8")

    return plan_folder


def get_plan_path(worktree_path: Path, git_ops=None) -> Path | None:
    """Get path to plan.md if it exists.

    Args:
        worktree_path: Path to the worktree directory
        git_ops: Optional GitOps interface for path checking (uses .exists() if None)

    Returns:
        Path to plan.md if exists, None otherwise
    """
    plan_file = worktree_path / ".plan" / "plan.md"
    path_exists = git_ops.path_exists(plan_file) if git_ops is not None else plan_file.exists()
    if path_exists:
        return plan_file
    return None


def get_progress_path(worktree_path: Path) -> Path | None:
    """Get path to progress.md if it exists.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        Path to progress.md if exists, None otherwise
    """
    progress_file = worktree_path / ".plan" / "progress.md"
    if progress_file.exists():
        return progress_file
    return None


def update_progress(worktree_path: Path, progress_content: str) -> None:
    """Update progress.md with new content.

    Args:
        worktree_path: Path to the worktree directory
        progress_content: New content for progress.md
    """
    progress_file = worktree_path / ".plan" / "progress.md"
    progress_file.write_text(progress_content, encoding="utf-8")


def extract_steps_from_plan(plan_content: str) -> list[str]:
    """Extract numbered steps from plan markdown.

    Handles various numbering formats:
    - "1. Step description"
    - "1) Step description"
    - "Step 1: description"
    - Nested: "1.1", "1.2", "2.1"

    Args:
        plan_content: Full plan markdown content

    Returns:
        List of step descriptions with their numbers
    """
    steps = []
    lines = plan_content.split("\n")

    # Patterns for step detection
    # Match: "1. ", "1) ", "1.1. ", "1.1) "
    numbered_pattern = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]")

    # Match: "Step 1:", "Step 1.1:"
    step_word_pattern = re.compile(r"^\s*Step (\d+(?:\.\d+)*):?")

    for line in lines:
        # Check numbered pattern first
        match = numbered_pattern.match(line)
        if match:
            # Extract the full line as step description
            step_text = line.strip()
            steps.append(step_text)
            continue

        # Check "Step X:" pattern
        match = step_word_pattern.match(line)
        if match:
            step_text = line.strip()
            steps.append(step_text)

    return steps


def _generate_progress_content(steps: list[str]) -> str:
    """Generate progress.md content with pre-populated checkboxes.

    Args:
        steps: List of step descriptions

    Returns:
        Formatted progress markdown with unchecked boxes
    """
    if not steps:
        return "# Progress Tracking\n\nNo steps detected in plan.\n"

    lines = ["# Progress Tracking\n"]

    for step in steps:
        # Create checkbox: - [ ] Step description
        lines.append(f"- [ ] {step}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)
