"""Submit plan for remote AI implementation via GitHub Actions."""

import subprocess

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_folder import copy_plan_to_submission, get_submission_path
from erk.core.repo_discovery import RepoContext


@click.command("submit")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_obj
def submit_cmd(ctx: ErkContext, dry_run: bool) -> None:
    """Submit plan for remote AI implementation via GitHub Actions.

    Copies .plan/ folder to .submission/, commits it, pushes to remote,
    and triggers the GitHub Actions workflow for implementation.

    Requires:
    - Current directory must have a .plan/ folder
    - Must be on a branch (not detached HEAD)
    """
    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Check for .plan/ folder
    plan_folder = ctx.cwd / ".plan"
    if not plan_folder.exists():
        user_output(
            click.style("Error: ", fg="red") + "No .plan/ folder found.\n\n"
            "The current directory must contain a .plan/ folder.\n"
            "To create one, use: /erk:create-planned-wt"
        )
        raise SystemExit(1)

    # Check if .submission/ already exists
    if get_submission_path(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red") + ".submission/ folder already exists.\n\n"
            "This usually means a submission is in progress.\n"
            "To clean up, delete the folder manually: rm -rf .submission/"
        )
        raise SystemExit(1)

    # Get current branch
    current_branch = ctx.git.get_current_branch(repo.root)
    if current_branch is None:
        user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
        raise SystemExit(1)

    user_output(f"Submitting plan from: {click.style(str(ctx.cwd), fg='yellow')}")
    user_output(f"Current branch: {click.style(current_branch, fg='cyan')}")
    user_output("")

    if dry_run:
        dry_run_msg = click.style("(dry run)", fg="bright_black")
        user_output(f"{dry_run_msg} Would copy .plan/ to .submission/")
        user_output(f"{dry_run_msg} Would commit and push .submission/")
        user_output(f"{dry_run_msg} Would trigger GitHub Actions workflow")
        return

    # Copy .plan/ to .submission/
    user_output("Copying .plan/ to .submission/...")
    copy_plan_to_submission(ctx.cwd)

    # Stage and commit .submission/ folder
    user_output("Committing .submission/ folder...")
    subprocess.run(
        ["git", "add", ".submission/"],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Submit plan for AI implementation\n\n"
            "This commit signals GitHub Actions to begin implementation.",
        ],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    # Push branch
    user_output("Pushing branch...")
    subprocess.run(
        ["git", "push", "-u", "origin", current_branch],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    # Trigger workflow
    workflow = "implement-plan.yml"
    user_output(f"Triggering workflow: {click.style(workflow, fg='cyan')}")
    ctx.github.trigger_workflow(
        repo.root,
        workflow,
        {"branch-name": current_branch},
    )

    user_output("")
    user_output(click.style("✓", fg="green") + " Submission complete!")
    user_output("")
    user_output("Monitor progress:")
    user_output("  gh run list --workflow=implement-plan.yml")
    user_output("  gh run watch")
