#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Submit current branch with comprehensive commit message.

This script provides subcommands for the gt submit-branch workflow:
- prepare: Commit outstanding changes and squash commits
- submit: Submit branch as PR and update PR metadata

The command layer orchestrates these steps with agent invocation in between.

Usage:
    uv run submit_branch.py prepare
    uv run submit_branch.py submit <commit_message>
    uv run submit_branch.py amend <commit_message>
    uv run submit_branch.py update-pr <commit_message>

Commands:
    prepare: Stage uncommitted changes, commit, and squash
    submit: Submit branch with gt submit --publish
    amend: Amend commit message
    update-pr: Update PR title and body to match commit message

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or submission failed)

Error Types:
    - no_changes: No changes to commit
    - squash_failed: Failed to squash commits
    - submit_failed: Failed to submit branch
    - branch_diverged: Branch diverged from remote
    - amend_failed: Failed to amend commit
    - pr_update_failed: Failed to update PR metadata

Examples:
    $ uv run submit_branch.py prepare
    {"success": true, "status": "prepared", "branch": "feature-branch", "parent": "main"}

    $ uv run submit_branch.py submit "Full commit message..."
    {"success": true, "pr_number": 123, "pr_url": "...", "branch": "feature-branch"}
"""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Literal

ErrorType = Literal[
    "no_changes",
    "squash_failed",
    "analysis_failed",
    "submit_failed",
    "branch_diverged",
    "amend_failed",
    "pr_update_failed",
]


@dataclass(frozen=True)
class SubmitBranchSuccess:
    """Success result from submitting a branch."""

    success: bool
    pr_number: int | None
    pr_url: str | None
    branch_name: str
    commit_message: str
    message: str


@dataclass(frozen=True)
class SubmitBranchError:
    """Error result from submitting a branch."""

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


def has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def commit_changes(message: str) -> bool:
    """Stage and commit all changes. Returns True on success."""
    # Stage all changes
    add_result = subprocess.run(
        ["git", "add", "."],
        capture_output=True,
        text=True,
        check=False,
    )
    if add_result.returncode != 0:
        return False

    # Commit with message
    commit_result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    return commit_result.returncode == 0


def squash_commits() -> bool:
    """Squash all commits in current branch. Returns True on success."""
    result = subprocess.run(
        ["gt", "squash"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def get_parent_branch() -> str | None:
    """Get the parent branch using gt branch. Returns None if command fails."""
    result = subprocess.run(
        ["gt", "branch", "--parent"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_branch_diff(parent_branch: str) -> str | None:
    """Get git diff between parent and current branch. Returns None on failure."""
    result = subprocess.run(
        ["git", "diff", f"{parent_branch}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout


def analyze_changes_with_agent(diff_content: str) -> str | None:
    """Invoke git-diff-summarizer agent to analyze changes.

    This requires the Claude Code CLI to be available and configured.
    Returns the analysis markdown or None on failure.
    """
    # For now, return None to indicate agent invocation is handled by the command
    # The actual agent invocation should be done by the Claude Code command layer
    # This is a placeholder that indicates the agent should be invoked
    return None


def amend_commit_message(message: str) -> bool:
    """Amend the current commit with a new message. Returns True on success."""
    result = subprocess.run(
        ["git", "commit", "--amend", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def submit_branch() -> tuple[bool, str]:
    """Submit branch with gt submit. Returns (success, output)."""
    result = subprocess.run(
        ["gt", "submit", "--publish", "--no-interactive", "--restack"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check for divergence errors
    output = result.stdout + result.stderr
    if "updated remotely" in output.lower() or "must sync" in output.lower():
        return False, "branch_diverged"

    if result.returncode != 0:
        return False, output

    return True, result.stdout


def get_pr_info() -> tuple[int, str] | None:
    """Get PR number and URL for current branch. Returns (number, url) or None."""
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


def update_pr_metadata(title: str, body: str) -> bool:
    """Update PR title and body. Returns True on success."""
    result = subprocess.run(
        ["gh", "pr", "edit", "--title", title, "--body", body],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def extract_title_and_body(commit_message: str) -> tuple[str, str]:
    """Extract title (first line) and body (rest) from commit message."""
    lines = commit_message.split("\n", 1)
    title = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    return title, body


@dataclass(frozen=True)
class PrepareResult:
    """Result from prepare subcommand."""

    success: bool
    status: str  # "prepared"
    branch: str
    parent: str
    message: str


def prepare_branch() -> PrepareResult | SubmitBranchError:
    """Prepare branch for submission: commit changes and squash.

    Returns:
        PrepareResult with branch and parent info, or SubmitBranchError
    """
    # Step 1: Get current branch
    branch_name = get_current_branch()

    # Step 2: Check for uncommitted changes and commit if present
    if has_uncommitted_changes():
        if not commit_changes("WIP: Prepare for submission"):
            return SubmitBranchError(
                success=False,
                error_type="no_changes",
                message="Failed to commit uncommitted changes",
                details={"current_branch": branch_name},
            )

    # Step 3: Squash commits
    if not squash_commits():
        return SubmitBranchError(
            success=False,
            error_type="squash_failed",
            message="Failed to squash commits in current branch",
            details={"current_branch": branch_name},
        )

    # Step 4: Get parent branch for diff
    parent = get_parent_branch()
    if parent is None:
        return SubmitBranchError(
            success=False,
            error_type="squash_failed",
            message="Could not determine parent branch",
            details={"current_branch": branch_name},
        )

    return PrepareResult(
        success=True,
        status="prepared",
        branch=branch_name,
        parent=parent,
        message=f"Prepared branch {branch_name} for submission (parent: {parent})",
    )


def amend_commit(commit_message: str) -> SubmitBranchSuccess | SubmitBranchError:
    """Amend current commit with provided message.

    Args:
        commit_message: The full commit message to use

    Returns:
        Success or error result
    """
    branch_name = get_current_branch()

    if not amend_commit_message(commit_message):
        return SubmitBranchError(
            success=False,
            error_type="amend_failed",
            message="Failed to amend commit message",
            details={"current_branch": branch_name},
        )

    return SubmitBranchSuccess(
        success=True,
        pr_number=None,
        pr_url=None,
        branch_name=branch_name,
        commit_message=commit_message,
        message=f"Amended commit message for branch {branch_name}",
    )


def submit_branch_command() -> SubmitBranchSuccess | SubmitBranchError:
    """Submit branch as PR using gt submit.

    Returns:
        Success with PR info or error result
    """
    branch_name = get_current_branch()

    # Execute gt submit
    success, output = submit_branch()

    if not success:
        if output == "branch_diverged":
            return SubmitBranchError(
                success=False,
                error_type="branch_diverged",
                message=(
                    "Branch has been updated remotely and diverged from local.\n\n"
                    "Please resolve with: gt sync\n"
                    "Then try again."
                ),
                details={"current_branch": branch_name},
            )

        return SubmitBranchError(
            success=False,
            error_type="submit_failed",
            message=f"Failed to submit branch: {output}",
            details={"current_branch": branch_name, "output": output},
        )

    # Get PR info after submission
    pr_info = get_pr_info()
    if pr_info is None:
        # PR might not exist yet (new branch), return success without PR info
        return SubmitBranchSuccess(
            success=True,
            pr_number=None,
            pr_url=None,
            branch_name=branch_name,
            commit_message="",
            message=f"Submitted branch {branch_name}",
        )

    pr_number, pr_url = pr_info
    return SubmitBranchSuccess(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        branch_name=branch_name,
        commit_message="",
        message=f"Submitted branch {branch_name} as PR #{pr_number}",
    )


def update_pr_command(commit_message: str) -> SubmitBranchSuccess | SubmitBranchError:
    """Update PR title and body to match commit message.

    Args:
        commit_message: The commit message to sync to PR

    Returns:
        Success or error result
    """
    branch_name = get_current_branch()

    # Check if PR exists
    pr_info = get_pr_info()
    if pr_info is None:
        # No PR exists, skip update
        return SubmitBranchSuccess(
            success=True,
            pr_number=None,
            pr_url=None,
            branch_name=branch_name,
            commit_message=commit_message,
            message=f"No PR exists for branch {branch_name}, skipping metadata update",
        )

    pr_number, pr_url = pr_info

    # Extract title and body from commit message
    title, body = extract_title_and_body(commit_message)

    # Update PR
    if not update_pr_metadata(title, body):
        return SubmitBranchError(
            success=False,
            error_type="pr_update_failed",
            message=f"Failed to update PR #{pr_number} metadata",
            details={"current_branch": branch_name, "pr_number": pr_number},
        )

    return SubmitBranchSuccess(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        branch_name=branch_name,
        commit_message=commit_message,
        message=f"Updated PR #{pr_number} title and body",
    )


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if len(sys.argv) < 2:
        error = SubmitBranchError(
            success=False,
            error_type="submit_failed",
            message="Missing subcommand. Usage: submit_branch.py {prepare|amend|submit|update-pr}",
            details={},
        )
        print(json.dumps(asdict(error), indent=2), file=sys.stderr)
        return 1

    subcommand = sys.argv[1]

    try:
        result: PrepareResult | SubmitBranchSuccess | SubmitBranchError

        if subcommand == "prepare":
            result = prepare_branch()
        elif subcommand == "amend":
            if len(sys.argv) < 3:
                error = SubmitBranchError(
                    success=False,
                    error_type="amend_failed",
                    message="Missing commit message argument",
                    details={},
                )
                print(json.dumps(asdict(error), indent=2), file=sys.stderr)
                return 1
            commit_msg = sys.argv[2]
            result = amend_commit(commit_msg)
        elif subcommand == "submit":
            result = submit_branch_command()
        elif subcommand == "update-pr":
            if len(sys.argv) < 3:
                error = SubmitBranchError(
                    success=False,
                    error_type="pr_update_failed",
                    message="Missing commit message argument",
                    details={},
                )
                print(json.dumps(asdict(error), indent=2), file=sys.stderr)
                return 1
            commit_msg = sys.argv[2]
            result = update_pr_command(commit_msg)
        else:
            error = SubmitBranchError(
                success=False,
                error_type="submit_failed",
                message=f"Unknown subcommand: {subcommand}",
                details={"subcommand": subcommand},
            )
            print(json.dumps(asdict(error), indent=2), file=sys.stderr)
            return 1

        print(json.dumps(asdict(result), indent=2))

        if isinstance(result, SubmitBranchError):
            return 1

        return 0
    except subprocess.CalledProcessError as e:
        error = SubmitBranchError(
            success=False,
            error_type="submit_failed",
            message=f"Command failed: {e}",
            details={"error": str(e)},
        )
        print(json.dumps(asdict(error), indent=2), file=sys.stderr)
        return 1
    except Exception as e:
        error = SubmitBranchError(
            success=False,
            error_type="submit_failed",
            message=f"Unexpected error: {e}",
            details={"error": str(e)},
        )
        print(json.dumps(asdict(error), indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
