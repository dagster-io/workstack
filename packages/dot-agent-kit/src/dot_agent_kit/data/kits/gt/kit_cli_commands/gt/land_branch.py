"""Land a single PR from Graphite stack without affecting upstack branches.

This script safely lands a single branch from a Graphite stack by:
1. Validating the branch is exactly one level up from main
2. Checking an open pull request exists
3. Squash-merging the PR to main
4. Navigating to the child branch if exactly one exists (skips navigation if multiple children)

Usage:
    dot-agent run gt land-branch

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
    $ dot-agent run gt land-branch
    {"success": true, "pr_number": 123, ...}
"""

import json
from dataclasses import asdict, dataclass
from typing import Literal

import click

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.ops import GtKitOps
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKitOps

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


def execute_land_branch(ops: GtKitOps | None = None) -> LandBranchSuccess | LandBranchError:
    """Execute the land-branch workflow. Returns success or error result."""
    if ops is None:
        ops = RealGtKitOps()

    # Step 1: Get current branch
    branch_name = ops.git().get_current_branch()
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Get parent branch
    parent = ops.graphite().get_parent_branch()

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
    pr_info = ops.github().get_pr_state()
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
    children = ops.graphite().get_children_branches()

    # Step 6: Merge the PR
    if not ops.github().merge_pr():
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
        if ops.graphite().navigate_to_child():
            child_branch = children[0]

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


@click.command()
def land_branch() -> None:
    """Land a single PR from Graphite stack without affecting upstack branches."""
    try:
        result = execute_land_branch()
        # Single line summary instead of formatted JSON
        if isinstance(result, LandBranchSuccess):
            click.echo(f"✓ Merged PR #{result.pr_number} ({result.branch_name})")
        else:
            click.echo(f"✗ Failed to merge: {result.message}")

        if isinstance(result, LandBranchError):
            raise SystemExit(1)

    except Exception as e:
        error = LandBranchError(
            success=False,
            error_type="merge_failed",
            message=f"Unexpected error: {e}",
            details={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None
