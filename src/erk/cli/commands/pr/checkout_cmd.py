"""Checkout a pull request into a worktree.

This command fetches PR code and creates a worktree for local review/testing.
"""

import click
from erk_shared.output.output import user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
from erk.cli.core import worktree_path_for
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext


@click.command("checkout")
@click.argument("pr_reference")
@click.pass_obj
def pr_checkout(ctx: ErkContext, pr_reference: str) -> None:
    """Checkout a pull request into a worktree.

    PR_REFERENCE can be a plain number (123) or GitHub URL
    (https://github.com/owner/repo/pull/123).

    Examples:

        # Checkout by PR number
        erk pr checkout 123

        # Checkout by GitHub URL
        erk pr checkout https://github.com/owner/repo/pull/123
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_installed()

    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    pr_number = parse_pr_reference(pr_reference)

    # Get PR checkout info from GitHub
    pr_info = ctx.github.get_pr_checkout_info(repo.root, pr_number)
    if pr_info is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Could not find PR #{pr_number}\n\n"
            + "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    # Warn for closed/merged PRs
    if pr_info.state != "OPEN":
        user_output(click.style("Warning: ", fg="yellow") + f"PR #{pr_number} is {pr_info.state}")

    # Determine branch name strategy
    # For cross-repository PRs (forks), use pr/<number> to avoid conflicts
    # For same-repository PRs, use the actual branch name
    if pr_info.is_cross_repository:
        branch_name = f"pr/{pr_number}"
    else:
        branch_name = pr_info.head_ref_name

    # Check if branch already exists in a worktree
    existing_worktree = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        # Branch already exists in a worktree - emit script to activate it
        script = render_activation_script(
            worktree_path=existing_worktree,
            final_message=f'echo "Switched to existing worktree for PR #{pr_number}"',
            comment="pr checkout activate-script",
        )
        user_output(f"PR #{pr_number} already checked out at {existing_worktree}")
        click.echo(script)
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, check if branch exists locally first
    if pr_info.is_cross_repository:
        # Fetch PR ref directly
        ctx.git.fetch_pr_ref(repo.root, "origin", pr_number, branch_name)
    else:
        # Check if branch exists locally or on remote
        local_branches = ctx.git.list_local_branches(repo.root)
        if branch_name in local_branches:
            # Branch already exists locally - just need to create worktree
            pass
        else:
            # Check remote and fetch if needed
            remote_branches = ctx.git.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch_name}"
            if remote_ref in remote_branches:
                ctx.git.fetch_branch(repo.root, "origin", branch_name)
                ctx.git.create_tracking_branch(repo.root, branch_name, remote_ref)
            else:
                # Branch not on remote (maybe local-only PR?), fetch via PR ref
                ctx.git.fetch_pr_ref(repo.root, "origin", pr_number, branch_name)

    # Create worktree
    worktree_path = worktree_path_for(repo.worktrees_dir, branch_name)
    ctx.git.add_worktree(
        repo.root,
        worktree_path,
        branch=branch_name,
        ref=None,
        create_branch=False,
    )

    # Emit activation script
    script = render_activation_script(
        worktree_path=worktree_path,
        final_message=f'echo "Checked out PR #{pr_number} at $(pwd)"',
        comment="pr checkout activate-script",
    )
    user_output(f"Created worktree for PR #{pr_number} at {worktree_path}")
    click.echo(script)
