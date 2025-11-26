"""Command to validate plan format against Schema v2 requirements."""

import click
from erk_shared.output.output import user_output

from erk.cli.commands.plan.check_helpers import (
    validate_first_comment_exists,
    validate_plan_body_extractable,
    validate_plan_header_exists,
    validate_plan_header_schema,
)
from erk.cli.commands.plan.shared import parse_plan_identifier
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


@click.command("check")
@click.argument("identifier", type=str)
@click.pass_obj
def check_plan(ctx: ErkContext, identifier: str) -> None:
    """Validate a plan's format against Schema v2 requirements.

    Validates that a plan stored in a GitHub issue conforms to Schema v2:
    - Issue body has plan-header metadata block with required fields
    - First comment has plan-body metadata block with extractable content

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Parse identifier
    try:
        issue_number = parse_plan_identifier(identifier)
    except ValueError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    user_output(f"Validating plan #{issue_number}...")
    user_output("")

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to fetch issue: {e}")
        raise SystemExit(1) from e

    issue_body = issue.body if issue.body else ""

    # Run validation checks
    checks: list[tuple[bool, str]] = []

    # Check 1 & 2: plan-header validation
    checks.append(validate_plan_header_exists(issue_body))
    checks.append(validate_plan_header_schema(issue_body))

    # Fetch comments
    try:
        comments = ctx.issues.get_issue_comments(repo_root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to fetch comments: {e}")
        raise SystemExit(1) from e

    # Check 3 & 4: comment validation
    checks.append(validate_first_comment_exists(comments))
    if comments:
        checks.append(validate_plan_body_extractable(comments[0]))

    # Output results
    for passed, description in checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    # Determine overall result
    failed_count = sum(1 for passed, _ in checks if not passed)
    if failed_count == 0:
        user_output(click.style("Plan validation passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "checks" if failed_count > 1 else "check"
        user_output(
            click.style(f"Plan validation failed ({failed_count} {check_word} failed)", fg="red")
        )
        raise SystemExit(1)
