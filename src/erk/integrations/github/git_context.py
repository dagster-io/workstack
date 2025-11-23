"""Git context collection utilities for plan issue metadata."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def collect_plan_git_context(cwd: Path) -> dict[str, Any]:
    """Collect git state for plan issue metadata.

    Gathers git context including base commit SHA, branch name, recent commits,
    and timestamp for drift detection when returning to plans later.

    Args:
        cwd: Working directory to collect git context from

    Returns:
        Dictionary with keys:
        - base_commit: Full SHA of current HEAD
        - branch: Current branch name
        - recent_commits: List of recent commits (up to 5)
        - timestamp: ISO 8601 timestamp

    Raises:
        subprocess.CalledProcessError: If git operations fail
        ValueError: If in detached HEAD state or empty repo
    """
    # Get current commit SHA
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        base_commit = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if "ambiguous argument 'HEAD'" in e.stderr:
            raise ValueError("Cannot collect git context from empty repository (no commits)") from e
        raise

    # Get current branch (fails if detached)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if branch == "HEAD":
            raise ValueError("Cannot collect git context in detached HEAD state") from None
    except subprocess.CalledProcessError:
        raise ValueError("Cannot collect git context in detached HEAD state") from None

    # Get recent commits with details
    result = subprocess.run(
        ["git", "log", "-5", "--format=%H%x00%s%x00%an%x00%ar"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        parts = line.split("\x00")
        if len(parts) == 4:
            commits.append(
                {
                    "sha": parts[0][:7],  # Short SHA for readability
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                }
            )

    # Get current timestamp
    timestamp = datetime.now(UTC).isoformat()

    return {
        "base_commit": base_commit,
        "branch": branch,
        "recent_commits": commits,
        "timestamp": timestamp,
    }
