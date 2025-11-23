#!/usr/bin/env python3
"""Find most recent *-plan.md file at repository root.

This command provides atomic file discovery for plan files, replacing
the fragile bash pipeline: find + ls -t + head.

Used by:
- /erk:create-plan-issue-from-plan-file
- /erk:create-queued-plan

The command searches for files matching the pattern *-plan.md at the
repository root (maxdepth 1) and returns the most recent by modification time.

Usage:
    # Find most recent plan file in current repo
    dot-agent kit-command erk find-most-recent-plan-file

    # Find most recent plan file in specific repo
    dot-agent kit-command erk find-most-recent-plan-file --repo-root /path/to/repo

Output:
    JSON object with success status and file information

Exit Codes:
    0: Success (plan file found)
    1: Error (no plan files found or invalid repo root)

Examples:
    $ dot-agent kit-command erk find-most-recent-plan-file
    {
      "success": true,
      "plan_file": "/Users/foo/repo/my-feature-plan.md",
      "modified_at": "2025-11-23T10:00:00Z",
      "all_plan_files_count": 3
    }

    $ dot-agent kit-command erk find-most-recent-plan-file --repo-root /nonexistent
    {
      "success": false,
      "error": "invalid_repo_root",
      "message": "Repository root does not exist: /nonexistent"
    }

    $ dot-agent kit-command erk find-most-recent-plan-file
    {
      "success": false,
      "error": "no_plan_files_found",
      "message": "No *-plan.md files found at repository root: /Users/foo/repo"
    }
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click


@dataclass
class PlanFileSuccess:
    """Success result with plan file information."""

    success: bool
    plan_file: str
    modified_at: str
    all_plan_files_count: int


@dataclass
class PlanFileError:
    """Error result when plan file not found or invalid input."""

    success: bool
    error: str
    message: str


def get_repo_root() -> Path | None:
    """Get git repository root using git rev-parse.

    Returns:
        Path to repository root, or None if not in a git repository
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip())


def find_most_recent_plan_file(repo_root: Path) -> PlanFileSuccess | PlanFileError:
    """Find most recent *-plan.md file at repository root.

    Args:
        repo_root: Path to repository root directory

    Returns:
        PlanFileSuccess with file info, or PlanFileError if not found
    """
    # Validate repo root exists
    if not repo_root.exists():
        return PlanFileError(
            success=False,
            error="invalid_repo_root",
            message=f"Repository root does not exist: {repo_root}",
        )

    if not repo_root.is_dir():
        return PlanFileError(
            success=False,
            error="invalid_repo_root",
            message=f"Repository root is not a directory: {repo_root}",
        )

    # Find all *-plan.md files at root level only
    plan_files: list[Path] = []
    for item in repo_root.iterdir():
        if item.is_file() and item.name.endswith("-plan.md"):
            plan_files.append(item)

    # Check if any plan files found
    if not plan_files:
        return PlanFileError(
            success=False,
            error="no_plan_files_found",
            message=f"No *-plan.md files found at repository root: {repo_root}",
        )

    # Find most recent by modification time
    most_recent = max(plan_files, key=lambda p: p.stat().st_mtime)
    modified_time = datetime.fromtimestamp(most_recent.stat().st_mtime, tz=UTC)

    return PlanFileSuccess(
        success=True,
        plan_file=str(most_recent),
        modified_at=modified_time.isoformat(),
        all_plan_files_count=len(plan_files),
    )


@click.command()
@click.option(
    "--repo-root",
    type=click.Path(exists=False, path_type=Path),
    help="Repository root path (defaults to git rev-parse --show-toplevel)",
)
def find_most_recent_plan_file_cli(repo_root: Path | None) -> None:
    """Find most recent *-plan.md file at repository root.

    This command searches for plan files matching *-plan.md pattern
    at the repository root and returns the most recent by modification time.
    """
    # Determine repo root
    if repo_root is None:
        repo_root = get_repo_root()
        if repo_root is None:
            error = PlanFileError(
                success=False,
                error="not_in_git_repo",
                message="Not in a git repository. Use --repo-root to specify path.",
            )
            click.echo(json.dumps(asdict(error), indent=2))
            raise SystemExit(1)

    # Find most recent plan file
    result = find_most_recent_plan_file(repo_root)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code on failure
    if isinstance(result, PlanFileError):
        raise SystemExit(1)
