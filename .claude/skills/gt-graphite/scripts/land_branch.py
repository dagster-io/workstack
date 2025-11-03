#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Land a single PR from Graphite stack without affecting upstack branches.

This script safely lands a single branch from a Graphite stack by:
1. Validating the branch is exactly one level up from main
2. Checking an open pull request exists
3. Squash-merging the PR to main
4. Navigating to the child branch if exactly one exists (skips navigation if multiple children)

Usage:
    uv run land_branch.py

Output:
    JSON object with either success or error information:

    Success:
    {
      "success": true,
      "pr_number": 123,
      "branch_name": "feature-branch",
      "child_branch": "next-feature",
      "message": "Successfully merged PR #123 for branch feature-branch"
    }

    Error:
    {
      "success": false,
      "error_type": "parent_not_main",
      "message": "Detailed error message...",
      "details": {...}
    }

Exit Codes:
    0: Success
    1: Error (validation failed or merge failed)

Error Types:
    - parent_not_main: Branch parent is not "main"
    - no_pr_found: No PR exists for this branch
    - pr_not_open: PR exists but is not in OPEN state
    - merge_failed: PR merge operation failed

Examples:
    $ uv run land_branch.py
    {"success": true, "pr_number": 123, ...}
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Literal

ErrorType = Literal[
    "parent_not_main",
    "no_pr_found",
    "pr_not_open",
    "merge_failed",
]


@dataclass
class LandBranchSuccess:
    """Success result from landing a branch."""

    success: bool
    pr_number: int
    branch_name: str
    child_branch: str | None
    message: str


@dataclass
class LandBranchError:
    """Error result from landing a branch."""

    success: bool
    error_type: ErrorType
    message: str
    details: dict[str, str | int | list[str]]


def get_current_branch() -> str:
    """Get the name of the current branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_parent_branch() -> str | None:
    """Get the parent branch using gt parent. Returns None if command fails."""
    result = subprocess.run(
        ["gt", "parent"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_children_branches() -> list[str]:
    """Get list of child branches using gt children. Returns empty list if command fails."""
    result = subprocess.run(
        ["gt", "children"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    # gt children outputs one branch per line
    children = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return children


def get_pr_info() -> tuple[int, str] | None:
    """Get PR number and state for current branch. Returns (number, state) or None."""
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "state,number"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    return (data["number"], data["state"])


def merge_pr() -> bool:
    """Merge the PR using squash merge. Returns True on success."""
    result = subprocess.run(
        ["gh", "pr", "merge", "-s"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def navigate_to_child(child_name: str) -> bool:
    """Navigate to child branch using gt up. Returns True on success."""
    result = subprocess.run(
        ["gt", "up"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def land_branch() -> LandBranchSuccess | LandBranchError:
    """Execute the land-branch workflow. Returns success or error result."""

    # Step 1: Get current branch
    branch_name = get_current_branch()

    # Step 2: Get parent branch
    parent = get_parent_branch()

    if parent is None:
        return LandBranchError(
            success=False,
            error_type="parent_not_main",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"current_branch": branch_name},
        )

    # Step 3: Validate parent is main
    if parent != "main":
        return LandBranchError(
            success=False,
            error_type="parent_not_main",
            message=(
                f"Branch must be exactly one level up from main\n"
                f"Current branch: {branch_name}\n"
                f"Parent branch: {parent} (expected: main)\n\n"
                f"Please navigate to a branch that branches directly from main."
            ),
            details={
                "current_branch": branch_name,
                "parent_branch": parent,
            },
        )

    # Step 4: Check PR exists and is open
    pr_info = get_pr_info()
    if pr_info is None:
        return LandBranchError(
            success=False,
            error_type="no_pr_found",
            message=(
                "No pull request found for this branch\n\nPlease create a PR first using: gt submit"
            ),
            details={"current_branch": branch_name},
        )

    pr_number, pr_state = pr_info
    if pr_state != "OPEN":
        return LandBranchError(
            success=False,
            error_type="pr_not_open",
            message=(
                f"Pull request is not open (state: {pr_state})\n\n"
                f"This command only works with open pull requests."
            ),
            details={
                "current_branch": branch_name,
                "pr_number": pr_number,
                "pr_state": pr_state,
            },
        )

    # Step 5: Get children branches
    children = get_children_branches()

    # Step 6: Merge the PR
    if not merge_pr():
        return LandBranchError(
            success=False,
            error_type="merge_failed",
            message=(f"Failed to merge PR #{pr_number}\n\nPlease resolve the issue and try again."),
            details={
                "current_branch": branch_name,
                "pr_number": pr_number,
            },
        )

    # Step 7: Navigate to child if exactly one exists
    child_branch = None
    if len(children) == 1:
        child_name = children[0]
        if navigate_to_child(child_name):
            child_branch = child_name

    # Build success message with navigation info
    if len(children) == 0:
        message = f"Successfully merged PR #{pr_number} for branch {branch_name}"
    elif len(children) == 1:
        if child_branch:
            message = (
                f"Successfully merged PR #{pr_number} for branch {branch_name}\n"
                f"Navigated to child branch: {child_branch}"
            )
        else:
            message = (
                f"Successfully merged PR #{pr_number} for branch {branch_name}\n"
                f"Failed to navigate to child: {children[0]}"
            )
    else:
        children_list = ", ".join(children)
        message = (
            f"Successfully merged PR #{pr_number} for branch {branch_name}\n"
            f"Multiple children detected: {children_list}\n"
            f"Run 'gt up' to navigate to a child branch"
        )

    return LandBranchSuccess(
        success=True,
        pr_number=pr_number,
        branch_name=branch_name,
        child_branch=child_branch,
        message=message,
    )


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        result = land_branch()
        print(json.dumps(asdict(result), indent=2))

        if isinstance(result, LandBranchError):
            return 1

        return 0
    except subprocess.CalledProcessError as e:
        error = LandBranchError(
            success=False,
            error_type="merge_failed",
            message=f"Command failed: {e}",
            details={"error": str(e)},
        )
        print(json.dumps(asdict(error), indent=2), file=sys.stderr)
        return 1
    except Exception as e:
        error = LandBranchError(
            success=False,
            error_type="merge_failed",
            message=f"Unexpected error: {e}",
            details={"error": str(e)},
        )
        print(json.dumps(asdict(error), indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
