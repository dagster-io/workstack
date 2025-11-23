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

import click

from erk.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKit


def execute_simple_submit(description: str | None = None, verbose: bool = False) -> dict:
    """Execute the simplified submit preparation phase.

    Args:
        description: Optional description for the commit
        verbose: Show detailed diagnostic output

    Returns:
        JSON dict with:
        - success: bool
        - diff: str (if successful)
        - branch: str (if successful)
        - parent: str (if successful)
        - error: str (if failed)
    """
    kit = RealGtKit()

    # 1. Check for uncommitted changes and commit if any
    if verbose:
        click.echo("Debug: Checking for uncommitted changes...", err=True)
    if kit.git().has_uncommitted_changes():
        if verbose:
            click.echo("Debug: Found uncommitted changes, staging...", err=True)
        if not kit.git().add_all():
            if verbose:
                click.echo("Debug: Failed to stage changes", err=True)
            return {"success": False, "error": "Failed to stage changes"}

        commit_message = description or "WIP: Prepare for submission"
        if verbose:
            click.echo(f"Debug: Creating commit with message: {commit_message!r}", err=True)
        if not kit.git().commit(commit_message):
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
    result = kit.graphite().restack()
    if not result:
        if verbose:
            click.echo("Debug: Restack failed", err=True)
        return {"success": False, "error": "Failed to restack branch"}
    if verbose:
        click.echo("Debug: Restack successful", err=True)

    # 3. Get current branch and parent
    if verbose:
        click.echo("Debug: Getting current branch name...", err=True)
    branch = kit.git().get_current_branch()
    if not branch:
        if verbose:
            click.echo("Debug: Could not determine current branch", err=True)
        return {"success": False, "error": "Could not determine current branch"}
    if verbose:
        click.echo(f"Debug: Current branch = {branch}", err=True)

    if verbose:
        click.echo("Debug: Getting parent branch...", err=True)
    parent = kit.graphite().get_parent_branch()
    if not parent:
        if verbose:
            click.echo("Debug: Could not determine parent branch", err=True)
        return {"success": False, "error": "Could not determine parent branch"}
    if verbose:
        click.echo(f"Debug: Parent branch = {parent}", err=True)

    # 4. Get diff for AI analysis
    if verbose:
        click.echo("Debug: Getting diff to parent...", err=True)
    diff = kit.git().get_diff_to_parent(parent)
    if verbose:
        click.echo(f"Debug: Diff length = {len(diff)} bytes", err=True)

    return {"success": True, "diff": diff, "branch": branch, "parent": parent}


def complete_submission(commit_message: str, squash: bool = True, verbose: bool = False) -> dict:
    """Complete the submission by amending commit and submitting PR.

    Args:
        commit_message: The commit message to use
        squash: Whether to squash commits (default: True)
        verbose: Show detailed diagnostic output

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    kit = RealGtKit()

    # 1. Amend commit with final message
    if verbose:
        click.echo(f"Debug: Amending commit with message: {commit_message!r}", err=True)
    if not kit.git().amend_commit(commit_message):
        if verbose:
            click.echo("Debug: Failed to amend commit", err=True)
        return {"success": False, "error": "Failed to amend commit"}
    if verbose:
        click.echo("Debug: Successfully amended commit", err=True)

    # 2. Submit with appropriate flags
    # Note: Since GraphiteGtKit.submit() doesn't have a squash parameter yet,
    # we'll need to squash manually if multiple commits exist
    if squash:
        if verbose:
            click.echo("Debug: Checking if squashing is needed...", err=True)
        parent = kit.graphite().get_parent_branch()
        if parent:
            commit_count = kit.git().count_commits_in_branch(parent)
            if verbose:
                click.echo(f"Debug: Commit count in branch = {commit_count}", err=True)
            if commit_count > 1:
                # Squash commits first
                if verbose:
                    click.echo("Debug: Squashing commits...", err=True)
                squash_result = kit.graphite().squash_commits()
                if not squash_result.success:
                    if verbose:
                        click.echo(f"Debug: Squash failed: {squash_result.stderr}", err=True)
                    return {"success": False, "error": f"Failed to squash: {squash_result.stderr}"}
                if verbose:
                    click.echo("Debug: Successfully squashed commits", err=True)

    # 3. Submit the PR
    if verbose:
        click.echo("Debug: Submitting PR...", err=True)
    result = kit.graphite().submit(publish=True, restack=True)
    if verbose:
        click.echo(
            f"Debug: submit() returned: success={result.success}, "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}",
            err=True,
        )
    if not result.success:
        return {"success": False, "error": result.stderr}
    if verbose:
        click.echo("Debug: PR submitted successfully", err=True)

    # 4. Get PR info
    if verbose:
        click.echo("Debug: Getting PR info...", err=True)
    pr_info = kit.github().get_pr_info()
    if not pr_info:
        # PR might have been created but we can't get its info
        return {
            "success": True,
            "pr_number": None,
            "pr_url": None,
            "message": "PR submitted but could not retrieve PR info",
        }

    pr_number, pr_url = pr_info
    if verbose:
        click.echo(f"Debug: Found PR #{pr_number} at {pr_url}", err=True)

    # 5. Get Graphite URL if possible
    if verbose:
        click.echo("Debug: Getting Graphite PR URL...", err=True)
    graphite_url = kit.github().get_graphite_pr_url(pr_number)
    if verbose:
        click.echo(f"Debug: Graphite URL = {graphite_url}", err=True)

    return {"success": True, "pr_number": pr_number, "pr_url": pr_url, "graphite_url": graphite_url}


# Main entry point - single command with flags
@click.command()
@click.option("--prepare", is_flag=True, help="Run preparation phase")
@click.option("--complete", is_flag=True, help="Run completion phase")
@click.option("--description", help="Optional commit description (prepare phase)")
@click.option("--message", help="Commit message (complete phase)")
@click.option("--no-squash", is_flag=True, help="Don't squash commits (complete phase)")
@click.option("--verbose", is_flag=True, help="Show detailed diagnostic output")
def simple_submit(
    prepare: bool,
    complete: bool,
    description: str | None,
    message: str | None,
    no_squash: bool,
    verbose: bool,
) -> None:
    """Simplified Graphite submit workflow.

    Usage:
        # Prepare phase
        dot-agent run gt simple-submit --prepare [--description "..."]

        # Complete phase
        dot-agent run gt simple-submit --complete --message "..." [--no-squash]
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
        result = complete_submission(message, squash=not no_squash, verbose=verbose)

    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    simple_submit()
