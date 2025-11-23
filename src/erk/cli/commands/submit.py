"""Submit plan for remote AI implementation via GitHub Actions."""

import click
from erk_shared.impl_folder import copy_impl_to_worker_impl, get_worker_impl_path

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.cli.subprocess_utils import run_with_error_reporting
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


@click.command("submit")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_obj
def submit_cmd(ctx: ErkContext, dry_run: bool) -> None:
    """Submit plan for remote AI implementation via GitHub Actions.

    Copies .impl/ folder to .worker-impl/, commits it, pushes to remote,
    and triggers the GitHub Actions workflow for implementation.

    Requires:
    - Current directory must have a .impl/ folder
    - Must be on a branch (not detached HEAD)
    """
    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Check for .impl/ folder
    impl_folder = ctx.cwd / ".impl"
    if not impl_folder.exists():
        user_output(
            click.style("Error: ", fg="red") + "No .impl/ folder found.\n\n"
            "The current directory must contain a .impl/ folder.\n"
            "To create one, use: /erk:create-wt-from-plan-file"
        )
        raise SystemExit(1)

    # Check if .worker-impl/ already exists
    if get_worker_impl_path(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red") + ".worker-impl/ folder already exists.\n\n"
            "This usually means a submission is in progress.\n"
            "To clean up, delete the folder manually: rm -rf .worker-impl/"
        )
        raise SystemExit(1)

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
        raise SystemExit(1)

    user_output(f"Submitting plan from: {click.style(str(ctx.cwd), fg='yellow')}")
    user_output(f"Current branch: {click.style(current_branch, fg='cyan')}")
    user_output("")

    if dry_run:
        dry_run_msg = click.style("(dry run)", fg="bright_black")
        user_output(f"{dry_run_msg} Would copy .impl/ to .worker-impl/")
        user_output(f"{dry_run_msg} Would commit and push .worker-impl/")
        user_output(
            f"{dry_run_msg} GitHub Actions will auto-trigger on push "
            "(workflow detects .worker-impl/**)"
        )
        return

    # Copy .impl/ to .worker-impl/
    user_output("Copying .impl/ to .worker-impl/...")
    copy_impl_to_worker_impl(ctx.cwd)

    # Stage and commit .worker-impl/ folder
    user_output("Committing .worker-impl/ folder...")
    run_with_error_reporting(
        ["git", "add", ".worker-impl/"],
        cwd=ctx.cwd,
        error_prefix="Failed to stage .worker-impl/ folder",
    )

    run_with_error_reporting(
        [
            "git",
            "commit",
            "-m",
            "Submit plan for AI implementation\n\n"
            "This commit signals GitHub Actions to begin implementation.",
        ],
        cwd=ctx.cwd,
        error_prefix="Failed to commit .worker-impl/ folder",
    )

    # Push branch
    user_output("Pushing branch...")
    run_with_error_reporting(
        ["git", "push", "-u", "origin", current_branch],
        cwd=ctx.cwd,
        error_prefix="Failed to push branch to remote",
        troubleshooting=[
            "Check your network connection",
            "Verify git credentials: gh auth status",
            "Ensure remote 'origin' exists: git remote -v",
            "Check repository permissions",
        ],
        show_output=True,
    )

    # Verify branch exists on remote
    user_output("Verifying branch on remote...")
    if not ctx.git.branch_exists_on_remote(repo.root, "origin", current_branch):
        user_output(
            click.style("Error: ", fg="red")
            + "Branch push reported success but branch not found on remote.\n\n"
            "This may indicate a git configuration issue or network problem.\n"
            "Try pushing manually: "
            + click.style(f"git push -u origin {current_branch}", fg="yellow")
        )
        raise SystemExit(1)

    user_output("")
    user_output(
        click.style("✓", fg="green")
        + " Submission complete! GitHub Actions will begin implementation automatically."
    )
    user_output("")
    user_output("Monitor workflow runs:")
    user_output(f"  gh run list --branch {current_branch}")
    user_output("")
    user_output("Watch latest run:")
    user_output("  gh run watch")
