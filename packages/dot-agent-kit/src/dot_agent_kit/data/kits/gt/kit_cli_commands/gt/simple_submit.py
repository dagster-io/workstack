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
import sys
from pathlib import Path

import click
from erk_shared.impl_folder import has_issue_reference, read_issue_reference

from erk.data.kits.gt.kit_cli_commands.gt.ops import GtKit
from erk.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKit


class DebugLogger:
    """Logger that conditionally outputs debug messages based on verbose flag."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def log(self, message: str) -> None:
        """Log debug message if verbose mode is enabled."""
        if self.enabled:
            click.echo(f"Debug: {message}", err=True)


def execute_simple_submit(
    description: str | None = None, verbose: bool = False, ops: GtKit | None = None
) -> dict:
    """Execute the simplified submit preparation phase.

    Args:
        description: Optional description for the commit
        verbose: Show detailed diagnostic output
        ops: Optional GtKit instance for dependency injection

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

    # 1. Check for uncommitted changes and commit if any
    if verbose:
        click.echo("Debug: Checking for uncommitted changes...", err=True)
    if ops.git().has_uncommitted_changes():
        if verbose:
            click.echo("Debug: Found uncommitted changes, staging...", err=True)
        if not ops.git().add_all():
            if verbose:
                click.echo("Debug: Failed to stage changes", err=True)
            return {"success": False, "error": "Failed to stage changes"}

        commit_message = description or "WIP: Prepare for submission"
        if verbose:
            click.echo(f"Debug: Creating commit with message: {commit_message!r}", err=True)
        if not ops.git().commit(commit_message):
            if verbose:
                click.echo("Debug: Failed to commit changes", err=True)
            return {"success": False, "error": "Failed to commit changes"}
        if verbose:
            click.echo("Debug: Successfully committed changes", err=True)
    else:
        if verbose:
            click.echo("Debug: No uncommitted changes found", err=True)

    # 2. Restack to ensure clean state
    if verbose:
        click.echo("Debug: Restacking branch...", err=True)
    result = ops.graphite().restack()
    if not result:
        if verbose:
            click.echo("Debug: Restack failed", err=True)
        return {"success": False, "error": "Failed to restack branch"}
    if verbose:
        click.echo("Debug: Restack successful", err=True)

    # 3. Get current branch and parent
    if verbose:
        click.echo("Debug: Getting current branch name...", err=True)
    branch = ops.git().get_current_branch()
    if not branch:
        if verbose:
            click.echo("Debug: Could not determine current branch", err=True)
        return {"success": False, "error": "Could not determine current branch"}
    if verbose:
        click.echo(f"Debug: Current branch = {branch}", err=True)

    if verbose:
        click.echo("Debug: Getting parent branch...", err=True)
    parent = ops.graphite().get_parent_branch()
    if not parent:
        if verbose:
            click.echo("Debug: Could not determine parent branch", err=True)
        return {"success": False, "error": "Could not determine parent branch"}
    if verbose:
        click.echo(f"Debug: Parent branch = {parent}", err=True)

    # 4. Get diff for AI analysis
    if verbose:
        click.echo("Debug: Getting diff to parent...", err=True)
    diff = ops.git().get_diff_to_parent(parent)
    if verbose:
        click.echo(f"Debug: Diff length = {len(diff)} bytes", err=True)

    # 5. Check for issue reference in .impl/issue.json
    issue_number: int | None = None
    impl_dir = Path.cwd() / ".impl"
    if has_issue_reference(impl_dir):
        if verbose:
            click.echo("Debug: Found .impl/issue.json, reading issue reference...", err=True)
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number
            if verbose:
                click.echo(f"Debug: Issue reference = #{issue_number}", err=True)
        else:
            if verbose:
                click.echo("Debug: Failed to read issue reference", err=True)
    else:
        if verbose:
            click.echo("Debug: No .impl/issue.json found", err=True)

    return {
        "success": True,
        "diff": diff,
        "branch": branch,
        "parent": parent,
        "issue_number": issue_number,
    }


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
    parent = ops.graphite().get_parent_branch()
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
) -> dict:
    """Complete the submission by amending commit and submitting PR.

    Args:
        commit_message: The commit message to use
        squash: Whether to squash commits (default: True)
        verbose: Show detailed diagnostic output
        issue_number: Optional GitHub issue number for linking
        ops: Optional GtKit instance for dependency injection

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

    # Get PR info
    logger.log("Getting PR info...")
    pr_info = ops.github().get_pr_info()
    if not pr_info:
        return {
            "success": True,
            "pr_number": None,
            "pr_url": None,
            "message": "PR submitted but could not retrieve PR info",
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
