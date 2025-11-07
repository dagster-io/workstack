"""Update PR by staging changes, committing, restacking, and submitting.

This script streamlines the process of updating an existing PR in a Graphite stack.
It performs the following steps:

1. Check PR exists: Verifies current branch has an associated PR
2. Auto-stage and commit: Commits any uncommitted changes with default message
3. Restack: Restacks the branch with conflict detection
4. Submit: Updates the existing PR

Usage:
    dot-agent run gt update-pr

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (PR not found, restack conflicts, or submission failed)

Error Types:
    - no_pr: No PR associated with current branch
    - commit_failed: Failed to commit changes
    - restack_failed: Failed to restack (likely conflicts)
    - submit_failed: Failed to submit updates

Examples:
    $ dot-agent run gt update-pr
    {"success": true, "pr_number": 123, "pr_url": "https://...", ...}
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Literal

import click

ErrorType = Literal[
    "no_pr",
    "commit_failed",
    "restack_failed",
    "submit_failed",
]


@dataclass
class UpdatePRResult:
    """Success result from update-pr command."""

    success: bool
    pr_number: int
    pr_url: str
    branch_name: str
    had_changes: bool
    message: str


@dataclass
class UpdatePRError:
    """Error result from update-pr command."""

    success: bool
    error_type: ErrorType
    message: str
    details: dict[str, str]


def get_current_branch() -> str | None:
    """Get the name of the current branch. Returns None if command fails."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def check_pr_exists() -> tuple[int, str] | None:
    """Check if current branch has an associated PR. Returns (number, url) or None."""
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number,url"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    return (data["number"], data["url"])


def has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes. Returns True if changes exist."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return False

    return bool(result.stdout.strip())


def stage_and_commit_changes() -> bool:
    """Stage all changes and commit with default message. Returns True on success."""
    # Stage all changes
    result = subprocess.run(
        ["git", "add", "."],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return False

    # Commit with default message
    result = subprocess.run(
        ["git", "commit", "-m", "Update changes"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def restack_branch() -> bool:
    """Run gt restack in no-interactive mode. Returns True on success."""
    result = subprocess.run(
        ["gt", "restack", "--no-interactive"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def submit_updates() -> bool:
    """Run gt submit to update the PR. Returns True on success."""
    result = subprocess.run(
        ["gt", "submit"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def execute_update_pr() -> UpdatePRResult | UpdatePRError:
    """Execute the update-pr workflow. Returns success or error result."""

    # Step 1: Get current branch for context
    branch_name = get_current_branch()
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Check PR exists
    pr_info = check_pr_exists()

    if pr_info is None:
        return UpdatePRError(
            success=False,
            error_type="no_pr",
            message="No PR associated with current branch",
            details={"branch_name": branch_name},
        )

    pr_number, pr_url = pr_info

    # Step 3: Check for uncommitted changes
    had_changes = has_uncommitted_changes()

    if had_changes:
        # Step 4: Stage and commit changes
        if not stage_and_commit_changes():
            return UpdatePRError(
                success=False,
                error_type="commit_failed",
                message="Failed to commit uncommitted changes",
                details={"branch_name": branch_name},
            )

    # Step 5: Restack
    if not restack_branch():
        return UpdatePRError(
            success=False,
            error_type="restack_failed",
            message="Conflicts occurred during restack",
            details={"branch_name": branch_name},
        )

    # Step 6: Submit
    if not submit_updates():
        return UpdatePRError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit updates",
            details={"branch_name": branch_name},
        )

    # Build success message
    if had_changes:
        message = (
            f"Successfully updated PR #{pr_number}\n"
            f"Committed changes, restacked, and submitted updates"
        )
    else:
        message = (
            f"Successfully updated PR #{pr_number}\n"
            f"No uncommitted changes, restacked and submitted updates"
        )

    return UpdatePRResult(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        branch_name=branch_name,
        had_changes=had_changes,
        message=message,
    )


@click.command()
def update_pr() -> None:
    """Update PR by staging changes, committing, restacking, and submitting."""
    try:
        result = execute_update_pr()
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, UpdatePRError):
            raise SystemExit(1)

    except Exception as e:
        error = UpdatePRError(
            success=False,
            error_type="submit_failed",
            message=f"Unexpected error during update-pr: {e}",
            details={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None
