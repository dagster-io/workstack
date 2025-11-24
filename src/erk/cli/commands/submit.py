"""Submit issue for remote AI implementation via GitHub Actions."""

import subprocess
from datetime import UTC, datetime

import click
from erk_shared.erp_folder import create_erp_folder
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.naming import sanitize_branch_component

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext

# Label used to queue issues for automated implementation
ERK_QUEUE_LABEL = "erk-queue"
ERK_PLAN_LABEL = "erk-plan"


@click.command("submit")
@click.argument("issue_number", type=int)
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_number: int, dry_run: bool) -> None:
    """Submit issue for remote AI implementation via GitHub Actions.

    Adds the erk-queue label to the specified GitHub issue, which triggers
    the dispatch-erk-queue.yml GitHub Actions workflow for automated implementation.

    Arguments:
        ISSUE_NUMBER: GitHub issue number to submit for implementation

    Requires:
        - Issue must have erk-plan label
        - Issue must be OPEN
        - Issue must not already have erk-queue label
    """
    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo.root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Validate: must have erk-plan label
    if ERK_PLAN_LABEL not in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have {ERK_PLAN_LABEL} label\n\n"
            "Cannot submit non-plan issues for automated implementation.\n"
            "To create a plan, use: erk plan save"
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if issue.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"Issue #{issue_number} is {issue.state}\n\n"
            "Cannot submit closed issues for automated implementation."
        )
        raise SystemExit(1)

    # Validate: must not already have erk-queue label
    if ERK_QUEUE_LABEL in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} already has {ERK_QUEUE_LABEL} label\n\n"
            "This issue has already been submitted for automated implementation.\n"
            f"View issue: {issue.url}"
        )
        raise SystemExit(1)

    # Display issue details
    user_output("Submitting issue for automated implementation:")
    user_output(f"  Number: {click.style(f'#{issue_number}', fg='cyan')}")
    user_output(f"  Title:  {click.style(issue.title, fg='yellow')}")
    user_output(f"  State:  {click.style(issue.state, fg='green')}")
    user_output("")

    # Fetch plan content
    user_output("Fetching plan content...")
    try:
        plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    plan_content = plan.body
    issue_url = plan.url

    # Generate branch name from issue title
    branch_name = sanitize_branch_component(issue.title)

    if dry_run:
        dry_run_msg = click.style("(dry run)", fg="bright_black")
        user_output(f"{dry_run_msg} Would create branch: {branch_name}")
        user_output(f"{dry_run_msg} Would create .erp/ folder with plan")
        user_output(f"{dry_run_msg} Would commit and push .erp/ folder")
        user_output(f"{dry_run_msg} Would create draft PR")
        user_output(f"{dry_run_msg} Would add label: {ERK_QUEUE_LABEL}")
        user_output(f"{dry_run_msg} Would trigger GitHub Actions workflow")
        user_output("")
        user_output("GitHub Actions workflow:")
        user_output("  https://github.com/{owner}/{repo}/actions/workflows/dispatch-erk-queue.yml")
        return

    # Get trunk branch
    trunk_branch = ctx.trunk_branch
    if trunk_branch is None:
        user_output(click.style("Error: ", fg="red") + "Could not detect trunk branch")
        raise SystemExit(1)

    # Create branch from trunk
    user_output(f"Creating branch: {click.style(branch_name, fg='cyan')}")
    try:
        # Check if branch already exists locally
        existing_branches = ctx.git.list_local_branches(repo.root)
        if branch_name in existing_branches:
            user_output(
                click.style("Error: ", fg="red") + f"Branch '{branch_name}' already exists\n\n"
                "Please delete the existing branch first or choose a different issue."
            )
            raise SystemExit(1)

        # Create new branch from trunk
        ctx.git.create_branch(repo.root, branch_name, f"origin/{trunk_branch}")
        ctx.git.checkout_branch(repo.root, branch_name)
    except Exception as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to create branch: {e}")
        raise SystemExit(1) from None

    # Create .erp/ folder with plan
    user_output("Creating .erp/ folder with plan...")
    try:
        create_erp_folder(
            plan_content=plan_content,
            issue_number=issue_number,
            issue_url=issue_url,
            issue_title=issue.title,
            repo_root=repo.root,
        )
    except Exception as e:
        # Clean up branch on error
        user_output(click.style("Error: ", fg="red") + f"Failed to create .erp/ folder: {e}")
        user_output("Cleaning up branch...")
        try:
            ctx.git.checkout_branch(repo.root, trunk_branch)
            ctx.git.delete_branch(repo.root, branch_name, force=True)
        except Exception:
            pass
        raise SystemExit(1) from None

    # Commit .erp/ folder
    user_output("Committing plan...")
    try:
        subprocess.run(
            ["git", "add", ".erp"],
            cwd=repo.root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Add plan for issue #{issue_number}"],
            cwd=repo.root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # Clean up on error
        user_output(click.style("Error: ", fg="red") + f"Failed to commit: {e.stderr}")
        user_output("Cleaning up...")
        try:
            ctx.git.checkout_branch(repo.root, trunk_branch)
            ctx.git.delete_branch(repo.root, branch_name, force=True)
        except Exception:
            pass
        raise SystemExit(1) from None

    # Push branch to origin
    user_output("Pushing branch to origin...")
    try:
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=repo.root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # Clean up on error
        user_output(click.style("Error: ", fg="red") + f"Failed to push: {e.stderr}")
        user_output("Cleaning up...")
        try:
            ctx.git.checkout_branch(repo.root, trunk_branch)
            ctx.git.delete_branch(repo.root, branch_name, force=True)
        except Exception:
            pass
        raise SystemExit(1) from None

    # Create draft PR
    user_output("Creating draft PR...")
    try:
        pr_body = (
            f"Implementation of plan from issue #{issue_number}\n\n"
            f"{issue_url}\n\n"
            f"**Status:** Queued for implementation\n\n"
            f"This PR will be marked ready for review after implementation completes."
        )

        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--draft",
                "--title",
                issue.title,
                "--body",
                pr_body,
                "--head",
                branch_name,
            ],
            cwd=repo.root,
            capture_output=True,
            text=True,
            check=True,
        )

        pr_url = result.stdout.strip()
        user_output(click.style("✓", fg="green") + f" Draft PR created: {pr_url}")
    except subprocess.CalledProcessError as e:
        # Clean up on error
        user_output(click.style("Error: ", fg="red") + f"Failed to create PR: {e.stderr}")
        user_output("Cleaning up...")
        try:
            # Delete remote branch
            subprocess.run(
                ["git", "push", "origin", "--delete", branch_name],
                cwd=repo.root,
                check=True,
                capture_output=True,
                text=True,
            )
            # Delete local branch
            ctx.git.checkout_branch(repo.root, trunk_branch)
            ctx.git.delete_branch(repo.root, branch_name, force=True)
        except Exception:
            pass
        raise SystemExit(1) from None

    # Ensure erk-queue label is on issue (idempotent)
    user_output(f"Adding {ERK_QUEUE_LABEL} label...")
    ctx.issues.ensure_label_on_issue(repo.root, issue_number, ERK_QUEUE_LABEL)

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Get submitter from git config
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        submitted_by = result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fall back to "unknown" if git config fails
        submitted_by = "unknown"

    if not submitted_by:
        submitted_by = "unknown"

    validation_results = {
        "issue_is_open": True,
        "has_erk_plan_label": True,
        "no_erk_queue_label_before": True,
    }

    # Create and post queued event comment
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            issue_number=issue_number,
            validation_results=validation_results,
            expected_workflow="dispatch-erk-queue",
        )

        comment_body = render_erk_issue_event(
            title="🔄 Issue Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Issue submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{ERK_QUEUE_LABEL}` label has been added. The GitHub Actions workflow "
                f"`dispatch-erk-queue` will be triggered automatically via webhook.\n\n"
                f"Watch for the workflow start comment with a link to the action run."
            ),
        )

        user_output("Posting queued event comment...")
        ctx.issues.add_comment(repo.root, issue_number, comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        # Log warning but don't block workflow - label still triggers it
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow will still be triggered by label."
        )

    # Success output
    user_output("")
    user_output(
        click.style("✓", fg="green")
        + " Issue submitted! GitHub Actions will begin implementation automatically."
    )
    user_output("")
    user_output("Created:")
    user_output(f"  • Branch: {click.style(branch_name, fg='cyan')}")
    user_output(f"  • Draft PR: {pr_url}")
    user_output("")
    user_output("Next steps:")
    user_output(f"  • View PR: {pr_url}")
    user_output(f"  • View issue: {issue.url}")
    user_output("  • Monitor workflow runs:")
    user_output("    gh run list --workflow=dispatch-erk-queue.yml")
    user_output("")
    user_output("  • Watch latest run:")
    user_output("    gh run watch")
    user_output("")
