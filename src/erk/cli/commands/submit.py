"""Submit issue for remote AI implementation via GitHub Actions."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


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
    if "erk-plan" not in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have erk-plan label\n\n"
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
    if "erk-queue" in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} already has erk-queue label\n\n"
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

    if dry_run:
        dry_run_msg = click.style("(dry run)", fg="bright_black")
        user_output(f"{dry_run_msg} Would add label: erk-queue")
        user_output(f"{dry_run_msg} Would trigger GitHub Actions workflow")
        user_output("")
        user_output("GitHub Actions workflow:")
        user_output("  https://github.com/{owner}/{repo}/actions/workflows/dispatch-erk-queue.yml")
        return

    # Add erk-queue label to issue
    user_output("Adding erk-queue label...")
    ctx.issues.add_label_to_issue(repo.root, issue_number, "erk-queue")

    # Success output
    user_output("")
    user_output(
        click.style("✓", fg="green")
        + " Issue submitted! GitHub Actions will begin implementation automatically."
    )
    user_output("")
    user_output("Next steps:")
    user_output(f"  • View issue: {issue.url}")
    user_output("  • Monitor workflow runs:")
    user_output("    gh run list --workflow=dispatch-erk-queue.yml")
    user_output("")
    user_output("  • Watch latest run:")
    user_output("    gh run watch")
    user_output("")
