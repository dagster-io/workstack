"""Post GitHub comment documenting worktree creation.

This kit CLI command wraps add_worktree_creation_comment() for agent invocation.

Usage:
    dot-agent kit-command erk comment-worktree-creation <issue_number> <worktree_name> <branch_name>

Output:
    Silent on success (agent shows its own success message)
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (not in git repo, gh CLI failure, or issue not found)

Examples:
    $ dot-agent kit-command erk comment-worktree-creation 123 feature-name feature-branch
"""

import subprocess
from pathlib import Path

import click

from erk.core.github.issues import RealGitHubIssues
from erk.core.plan_folder import add_worktree_creation_comment


def get_repo_root() -> Path:
    """Get repository root using git rev-parse.

    Returns:
        Path to repository root

    Raises:
        RuntimeError: If not in a git repository or git command fails
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        msg = "Not in a git repository"
        raise RuntimeError(msg)

    return Path(result.stdout.strip())


@click.command(name="comment-worktree-creation")
@click.argument("issue_number", type=int)
@click.argument("worktree_name")
@click.argument("branch_name")
def comment_worktree_creation(issue_number: int, worktree_name: str, branch_name: str) -> None:
    """Post GitHub comment documenting worktree creation.

    ISSUE_NUMBER: GitHub issue number to comment on
    WORKTREE_NAME: Name of the created worktree
    BRANCH_NAME: Git branch name for the worktree
    """
    # Detect repo root
    try:
        repo_root = get_repo_root()
    except RuntimeError as e:
        click.echo(click.style("Error: ", fg="red") + str(e), err=True)
        raise SystemExit(1) from e

    # Create GitHub issues interface
    github_issues = RealGitHubIssues()

    # Post comment
    try:
        add_worktree_creation_comment(
            github_issues, repo_root, issue_number, worktree_name, branch_name
        )
    except RuntimeError as e:
        click.echo(
            click.style("Error: ", fg="red") + f"Failed to post comment: {e}",
            err=True,
        )
        raise SystemExit(1) from e

    # Silent success - agent will show its own success message
