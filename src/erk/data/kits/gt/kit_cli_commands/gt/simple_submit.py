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


def execute_simple_submit(description: str | None = None) -> dict:
    """Execute the simplified submit preparation phase.

    Args:
        description: Optional description for the commit

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
    if kit.git().has_uncommitted_changes():
        if not kit.git().add_all():
            return {"success": False, "error": "Failed to stage changes"}

        commit_message = description or "WIP: Prepare for submission"
        if not kit.git().commit(commit_message):
            return {"success": False, "error": "Failed to commit changes"}

    # 2. Restack to ensure clean state
    result = kit.graphite().restack()
    if not result:
        return {"success": False, "error": "Failed to restack branch"}

    # 3. Get current branch and parent
    branch = kit.git().get_current_branch()
    if not branch:
        return {"success": False, "error": "Could not determine current branch"}

    parent = kit.graphite().get_parent_branch()
    if not parent:
        return {"success": False, "error": "Could not determine parent branch"}

    # 4. Get diff for AI analysis
    diff = kit.git().get_diff_to_parent(parent)

    return {"success": True, "diff": diff, "branch": branch, "parent": parent}


def complete_submission(commit_message: str, squash: bool = True) -> dict:
    """Complete the submission by amending commit and submitting PR.

    Args:
        commit_message: The commit message to use
        squash: Whether to squash commits (default: True)

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    kit = RealGtKit()

    # 1. Amend commit with final message
    if not kit.git().amend_commit(commit_message):
        return {"success": False, "error": "Failed to amend commit"}

    # 2. Submit with appropriate flags
    # Note: Since GraphiteGtKit.submit() doesn't have a squash parameter yet,
    # we'll need to squash manually if multiple commits exist
    if squash:
        parent = kit.graphite().get_parent_branch()
        if parent:
            commit_count = kit.git().count_commits_in_branch(parent)
            if commit_count > 1:
                # Squash commits first
                squash_result = kit.graphite().squash_commits()
                if not squash_result.success:
                    return {"success": False, "error": f"Failed to squash: {squash_result.stderr}"}

    # 3. Submit the PR
    result = kit.graphite().submit(publish=True, restack=True)
    if not result.success:
        return {"success": False, "error": result.stderr}

    # 4. Get PR info
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

    # 5. Get Graphite URL if possible
    graphite_url = kit.github().get_graphite_pr_url(pr_number)

    return {"success": True, "pr_number": pr_number, "pr_url": pr_url, "graphite_url": graphite_url}


# Main entry point - single command with flags
@click.command()
@click.option("--prepare", is_flag=True, help="Run preparation phase")
@click.option("--complete", is_flag=True, help="Run completion phase")
@click.option("--description", help="Optional commit description (prepare phase)")
@click.option("--message", help="Commit message (complete phase)")
@click.option("--no-squash", is_flag=True, help="Don't squash commits (complete phase)")
def simple_submit(
    prepare: bool, complete: bool, description: str | None, message: str | None, no_squash: bool
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
        result = execute_simple_submit(description)
    else:  # complete
        if not message:
            click.echo("Error: --message is required for --complete", err=True)
            sys.exit(1)
        result = complete_submission(message, squash=not no_squash)

    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    simple_submit()
