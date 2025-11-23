"""Implementation folder utilities for erk and dot-agent-kit.

This module provides shared utilities for managing .impl/ folder structures:
- issue.json: GitHub issue reference management
- progress.md: Progress tracking with YAML front matter
- Worktree creation comments

These utilities are used by both erk (for local operations) and dot-agent-kit
(for kit CLI commands).
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from erk_shared.github.metadata import (
    create_worktree_creation_block,
    render_erk_issue_event,
)


def parse_progress_frontmatter(content: str) -> dict[str, Any] | None:
    """Parse YAML front matter from progress.md content.

    Args:
        content: Full progress.md file content

    Returns:
        Dictionary with 'completed_steps' and 'total_steps', or None if missing/invalid
    """
    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(content)
    except yaml.YAMLError:
        return None

    # Check for required fields
    metadata = post.metadata
    if "completed_steps" not in metadata or "total_steps" not in metadata:
        return None

    return metadata


@dataclass(frozen=True)
class IssueReference:
    """Reference to a GitHub issue associated with a plan."""

    issue_number: int
    issue_url: str
    created_at: str
    synced_at: str


def save_issue_reference(impl_dir: Path, issue_number: int, issue_url: str) -> None:
    """Save GitHub issue reference to .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    issue_file = impl_dir / "issue.json"
    now = datetime.now(UTC).isoformat()

    data = {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "created_at": now,
        "synced_at": now,
    }

    issue_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_issue_reference(impl_dir: Path) -> IssueReference | None:
    """Read GitHub issue reference from .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        IssueReference if file exists and is valid, None otherwise
    """
    issue_file = impl_dir / "issue.json"

    if not issue_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(issue_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    # Validate required fields exist
    if (
        "issue_number" not in data
        or "issue_url" not in data
        or "created_at" not in data
        or "synced_at" not in data
    ):
        return None

    return IssueReference(
        issue_number=data["issue_number"],
        issue_url=data["issue_url"],
        created_at=data["created_at"],
        synced_at=data["synced_at"],
    )


def has_issue_reference(impl_dir: Path) -> bool:
    """Check if .impl/issue.json exists.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if issue.json exists, False otherwise
    """
    issue_file = impl_dir / "issue.json"
    return issue_file.exists()


def add_worktree_creation_comment(
    github_issues,
    repo_root: Path,
    issue_number: int,
    worktree_name: str,
    branch_name: str,
) -> None:
    """Add a comment to the GitHub issue documenting worktree creation.

    Args:
        github_issues: GitHubIssues interface for posting comments
        repo_root: Repository root directory
        issue_number: GitHub issue number to comment on
        worktree_name: Name of the created worktree
        branch_name: Git branch name for the worktree

    Raises:
        RuntimeError: If gh CLI fails or issue not found
    """
    timestamp = datetime.now(UTC).isoformat()

    # Create metadata block with issue number
    block = create_worktree_creation_block(
        worktree_name=worktree_name,
        branch_name=branch_name,
        timestamp=timestamp,
        issue_number=issue_number,
    )

    # Format instructions for implementation
    instructions = f"""The worktree is ready for implementation. You can navigate to it using:
```bash
erk checkout {branch_name}
```

To implement the plan:
```bash
claude --permission-mode acceptEdits "/erk:implement-plan"
```"""

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title=f"✅ Worktree created: **{worktree_name}**",
        metadata=block,
        description=instructions,
    )

    github_issues.add_comment(repo_root, issue_number, comment_body)
