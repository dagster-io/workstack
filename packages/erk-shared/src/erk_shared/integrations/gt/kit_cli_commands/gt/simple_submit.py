"""Simplified Graphite submit workflow for testing and comparison.

This module provides a drastically simplified version of the Graphite submit
workflow as an alternative to the complex submit_branch.py implementation.

Design goals:
- Fail fast with natural error messages
- Single-phase execution
- Direct gt submit --squash instead of manual squashing
- Reuse existing RealGtKit operations
- Simple JSON output without complex error types
"""

import json
import subprocess
import sys
from pathlib import Path

import click

from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.real import RealTime


class DebugLogger:
    """Logger that conditionally outputs debug messages based on verbose flag."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def log(self, message: str) -> None:
        """Log debug message if verbose mode is enabled."""
        if self.enabled:
            click.echo(f"Debug: {message}", err=True)


def execute_simple_submit(
    description: str | None = None,
    verbose: bool = False,
    ops: GtKit | None = None,
    impl_dir: Path | None = None,
) -> dict:
    """Execute the simplified submit preparation phase.

    Args:
        description: Optional description for the commit
        verbose: Show detailed diagnostic output
        ops: Optional GtKit instance for dependency injection
        impl_dir: Optional path to .impl directory (defaults to Path.cwd() / ".impl")

    Returns:
        JSON dict with:
        - success: bool
        - diff: str (if successful)
        - branch: str (if successful)
        - parent: str (if successful)
        - error: str (if failed)
    """
    if ops is None:
        ops = RealGtKit()

    logger = DebugLogger(verbose)

    # Commit any uncommitted changes
    error = _commit_uncommitted_changes(ops, logger, description)
    if error is not None:
        return error

    # Restack branch
    error = _restack_branch(ops, logger)
    if error is not None:
        return error

    # Get branch info
    result = _get_branch_info(ops, logger)
    if result[0] is None:
        return result[1]

    branch, parent = result

    # Get diff for AI analysis
    logger.log("Getting diff to parent...")
    diff = ops.git().get_diff_to_parent(parent)
    logger.log(f"Diff length = {len(diff)} bytes")

    # Read issue reference if exists
    impl_dir = impl_dir or Path.cwd() / ".impl"
    issue_number = _read_issue_reference_if_exists(impl_dir, logger)

    return {
        "success": True,
        "diff": diff,
        "branch": branch,
        "parent": parent,
        "issue_number": issue_number,
    }


def _commit_uncommitted_changes(
    ops: GtKit, logger: DebugLogger, description: str | None
) -> dict | None:
    """Commit any uncommitted changes.

    Returns None if successful, error dict if failed.
    """
    logger.log("Checking for uncommitted changes...")
    if not ops.git().has_uncommitted_changes():
        logger.log("No uncommitted changes found")
        return None

    logger.log("Found uncommitted changes, staging...")
    if not ops.git().add_all():
        logger.log("Failed to stage changes")
        return {"success": False, "error": "Failed to stage changes"}

    commit_message = description or "WIP: Prepare for submission"
    logger.log(f"Creating commit with message: {commit_message!r}")
    if not ops.git().commit(commit_message):
        logger.log("Failed to commit changes")
        return {"success": False, "error": "Failed to commit changes"}

    logger.log("Successfully committed changes")
    return None


def _restack_branch(ops: GtKit, logger: DebugLogger) -> dict | None:
    """Restack branch to ensure clean state.

    Returns None if successful, error dict if failed.
    """
    logger.log("Restacking branch...")
    try:
        repo_root = Path(ops.git().get_repository_root())
        ops.main_graphite().restack(repo_root, no_interactive=True, quiet=False)
        logger.log("Restack successful")
        return None
    except subprocess.CalledProcessError:
        logger.log("Restack failed")
        return {"success": False, "error": "Failed to restack branch"}


def _get_branch_info(ops: GtKit, logger: DebugLogger) -> tuple[str, str] | tuple[None, dict]:
    """Get current branch and parent branch.

    Returns (branch, parent) tuple on success, (None, error_dict) on failure.
    """
    logger.log("Getting current branch name...")
    branch = ops.git().get_current_branch()
    if not branch:
        logger.log("Could not determine current branch")
        return None, {"success": False, "error": "Could not determine current branch"}
    logger.log(f"Current branch = {branch}")

    logger.log("Getting parent branch...")
    repo_root = Path(ops.git().get_repository_root())
    parent = ops.main_graphite().get_parent_branch(ops.git(), repo_root, branch)
    if not parent:
        logger.log("Could not determine parent branch")
        return None, {"success": False, "error": "Could not determine parent branch"}
    logger.log(f"Parent branch = {parent}")

    return branch, parent


def _read_issue_reference_if_exists(impl_dir: Path, logger: DebugLogger) -> int | None:
    """Read issue reference from .impl/issue.json if it exists.

    Returns issue number if found, None otherwise.
    """
    if not has_issue_reference(impl_dir):
        logger.log("No .impl/issue.json found")
        return None

    logger.log("Found .impl/issue.json, reading issue reference...")
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        logger.log("Failed to read issue reference")
        return None

    logger.log(f"Issue reference = #{issue_ref.issue_number}")
    return issue_ref.issue_number


def _stage_uncommitted_changes(ops: GtKit, logger: DebugLogger) -> dict | None:
    """Stage uncommitted changes before amending commit.

    Returns None if successful, error dict if failed.
    """
    logger.log("Checking for uncommitted changes before amend...")
    if not ops.git().has_uncommitted_changes():
        logger.log("No uncommitted changes found")
        return None

    logger.log("Found uncommitted changes, staging...")
    if not ops.git().add_all():
        logger.log("Failed to stage changes")
        return {"success": False, "error": "Failed to stage changes"}

    logger.log("Successfully staged changes")
    return None


def _prepare_commit_message(
    commit_message: str, issue_number: int | None, logger: DebugLogger
) -> str:
    """Prepare final commit message with optional issue reference."""
    if issue_number is None:
        return commit_message

    logger.log(f"Adding issue reference #{issue_number} to commit message")
    return f"{commit_message}\n\nCloses #{issue_number}"


def _amend_commit(ops: GtKit, logger: DebugLogger, message: str) -> dict | None:
    """Amend commit with final message.

    Returns None if successful, error dict if failed.
    """
    logger.log(f"Amending commit with message: {message!r}")
    if not ops.git().amend_commit(message):
        logger.log("Failed to amend commit")
        return {"success": False, "error": "Failed to amend commit"}

    logger.log("Successfully amended commit")
    return None


def _squash_if_needed(ops: GtKit, logger: DebugLogger, should_squash: bool) -> dict | None:
    """Squash commits if multiple exist and squash flag is True.

    Returns None if successful/not needed, error dict if failed.
    """
    if not should_squash:
        return None

    logger.log("Checking if squashing is needed...")
    repo_root = Path(ops.git().get_repository_root())
    current_branch = ops.git().get_current_branch()
    if not current_branch:
        return None
    parent = ops.main_graphite().get_parent_branch(ops.git(), repo_root, current_branch)
    if not parent:
        return None

    commit_count = ops.git().count_commits_in_branch(parent)
    logger.log(f"Commit count in branch = {commit_count}")

    if commit_count <= 1:
        return None

    logger.log("Squashing commits...")
    squash_result = ops.graphite().squash_commits()
    if not squash_result.success:
        logger.log(f"Squash failed: {squash_result.stderr}")
        return {"success": False, "error": f"Failed to squash: {squash_result.stderr}"}

    logger.log("Successfully squashed commits")
    return None


def _submit_pr(ops: GtKit, logger: DebugLogger) -> dict | None:
    """Submit the PR via Graphite.

    Returns None if successful, error dict if failed.
    """
    logger.log("Submitting PR...")
    result = ops.graphite().submit(publish=True, restack=True)
    logger.log(
        f"submit() returned: success={result.success}, "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )

    if not result.success:
        return {"success": False, "error": result.stderr}

    logger.log("PR submitted successfully")
    return None


def _get_pr_info(ops: GtKit, logger: DebugLogger, time: Time) -> tuple[int, str] | None:
    """Get PR info from GitHub with exponential backoff retry.

    The GitHub API may not immediately have PR info available after submission,
    so we retry with exponential backoff (1s, 2s, 4s) up to 3 attempts.

    Args:
        ops: GtKit operations instance
        logger: Debug logger
        time: Time abstraction for sleep operations

    Returns:
        Tuple of (pr_number, pr_url) if found, None otherwise
    """
    max_attempts = 3
    backoff_delays = [1, 2, 4]  # Exponential backoff in seconds

    for attempt in range(max_attempts):
        logger.log(f"Getting PR info (attempt {attempt + 1}/{max_attempts})...")
        pr_info = ops.github().get_pr_info()

        if pr_info is not None:
            logger.log(f"Found PR info on attempt {attempt + 1}")
            return pr_info

        if attempt < max_attempts - 1:
            delay = backoff_delays[attempt]
            logger.log(f"PR info not available, retrying in {delay}s...")
            time.sleep(delay)
        else:
            logger.log("PR info not available after all retries")

    return None


def _finalize_pr_metadata(
    ops: GtKit,
    logger: DebugLogger,
    pr_number: int,
    commit_message: str,
    issue_number: int | None,
) -> None:
    """Mark PR as ready and update metadata with issue reference if provided."""
    # Mark PR as ready for review
    logger.log("Marking PR as ready for review...")
    if not ops.github().mark_pr_ready():
        logger.log("Failed to mark PR as ready")
        # Don't fail the entire operation
    else:
        logger.log("Successfully marked PR as ready")

    # Update PR body with "Closes #N" if issue number provided
    if issue_number is None:
        return

    logger.log(f"Updating PR with issue reference #{issue_number}")
    lines = commit_message.split("\n", 1)
    pr_title = lines[0]
    pr_body = lines[1].lstrip() if len(lines) > 1 else ""
    pr_body_with_issue = f"{pr_body}\n\nCloses #{issue_number}"

    if not ops.github().update_pr_metadata(pr_title, pr_body_with_issue):
        logger.log("Failed to update PR metadata")
        # Don't fail the entire operation
    else:
        logger.log("Successfully updated PR metadata")


def complete_submission(
    commit_message: str,
    squash: bool = True,
    verbose: bool = False,
    issue_number: int | None = None,
    ops: GtKit | None = None,
    time: Time | None = None,
) -> dict:
    """Complete the submission by amending commit and submitting PR.

    Args:
        commit_message: The commit message to use
        squash: Whether to squash commits (default: True)
        verbose: Show detailed diagnostic output
        issue_number: Optional GitHub issue number for linking
        ops: Optional GtKit instance for dependency injection
        time: Optional Time instance for dependency injection

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - issue_number: int | None (if issue linking enabled)
        - error: str (if failed)
    """
    if ops is None:
        ops = RealGtKit()
    if time is None:
        time = RealTime()

    logger = DebugLogger(verbose)

    # Stage uncommitted changes
    error = _stage_uncommitted_changes(ops, logger)
    if error is not None:
        return error

    # Prepare commit message with issue reference
    final_commit_message = _prepare_commit_message(commit_message, issue_number, logger)

    # Amend commit
    error = _amend_commit(ops, logger, final_commit_message)
    if error is not None:
        return error

    # Squash if needed
    error = _squash_if_needed(ops, logger, squash)
    if error is not None:
        return error

    # Submit PR
    error = _submit_pr(ops, logger)
    if error is not None:
        return error

    # Get PR info with retry (may not be immediately available)
    pr_info = _get_pr_info(ops, logger, time)
    if pr_info is None:
        return {
            "success": True,
            "pr_number": None,
            "pr_url": None,
            "message": "PR submitted but could not retrieve PR info after retries",
        }

    pr_number, pr_url = pr_info
    logger.log(f"Found PR #{pr_number} at {pr_url}")

    # Finalize PR metadata (mark ready, update with issue reference)
    _finalize_pr_metadata(ops, logger, pr_number, commit_message, issue_number)

    # Get Graphite URL
    logger.log("Getting Graphite PR URL...")
    graphite_url = ops.github().get_graphite_pr_url(pr_number)
    logger.log(f"Graphite URL = {graphite_url}")

    return {
        "success": True,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "graphite_url": graphite_url,
        "issue_number": issue_number,
    }


# Main entry point - single command with flags
@click.command()
@click.option("--prepare", is_flag=True, help="Run preparation phase")
@click.option("--complete", is_flag=True, help="Run completion phase")
@click.option("--description", help="Optional commit description (prepare phase)")
@click.option("--message", help="Commit message (complete phase)")
@click.option("--issue-number", type=int, help="GitHub issue number for linking (complete phase)")
@click.option("--no-squash", is_flag=True, help="Don't squash commits (complete phase)")
@click.option("--verbose", is_flag=True, help="Show detailed diagnostic output")
def simple_submit(
    prepare: bool,
    complete: bool,
    description: str | None,
    message: str | None,
    issue_number: int | None,
    no_squash: bool,
    verbose: bool,
) -> None:
    """Simplified Graphite submit workflow.

    Usage:
        # Prepare phase
        dot-agent run gt simple-submit --prepare [--description "..."]

        # Complete phase
        dot-agent run gt simple-submit --complete --message "..." [--issue-number N] [--no-squash]
    """
    if prepare and complete:
        click.echo("Error: Cannot use --prepare and --complete together", err=True)
        sys.exit(1)

    if not prepare and not complete:
        click.echo("Error: Must specify either --prepare or --complete", err=True)
        sys.exit(1)

    if prepare:
        result = execute_simple_submit(description, verbose=verbose)
    else:  # complete
        if not message:
            click.echo("Error: --message is required for --complete", err=True)
            sys.exit(1)
        result = complete_submission(
            message, squash=not no_squash, verbose=verbose, issue_number=issue_number
        )

    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    simple_submit()
