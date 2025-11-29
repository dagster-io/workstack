"""Extract plan from Claude session and create GitHub issue.

Usage:
    dot-agent kit-command erk create-issue-from-session [--session-id SESSION_ID]

This command combines plan extraction from Claude session files with GitHub
issue creation. It extracts the latest ExitPlanMode plan, ensures the erk-plan
label exists, and creates a GitHub issue with the plan content.

SCHEMA VERSION 2: This command uses the new two-step creation flow:
1. Create issue with metadata-only body (using format_plan_header_body())
2. Add first comment with plan content (using format_plan_content_comment())

Output:
    JSON result on stdout: {"success": true, "issue_number": N, "issue_url": "..."}
    Error messages on stderr with exit code 1 on failure

Exit Codes:
    0: Success - issue created
    1: Error - no plan found, gh CLI not available, or other error
"""

import json
import subprocess
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import (
    format_plan_content_comment,
    format_plan_header_body,
)

from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan


def ensure_label_exists(label_name: str, label_color: str, label_description: str) -> None:
    """Ensure GitHub label exists, creating it if necessary.

    Args:
        label_name: Label name to create
        label_color: Label color (hex without #)
        label_description: Label description

    Raises:
        subprocess.CalledProcessError: If gh command fails
    """
    # Check if label exists
    result = subprocess.run(
        ["gh", "label", "list", "--json", "name"], capture_output=True, text=True, check=True
    )

    labels_data = json.loads(result.stdout)
    existing_labels = {label["name"] for label in labels_data}

    if label_name not in existing_labels:
        # Create label
        subprocess.run(
            [
                "gh",
                "label",
                "create",
                label_name,
                "--color",
                label_color,
                "--description",
                label_description,
            ],
            check=True,
            capture_output=True,
            text=True,
        )


def _get_github_username() -> str | None:
    """Get current GitHub username from gh CLI.

    Returns:
        GitHub username or None if not authenticated
    """
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


@click.command(name="create-issue-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
def create_issue_from_session(session_id: str | None) -> None:
    """Extract plan from Claude session and create GitHub issue.

    Combines plan extraction with GitHub issue creation in a single operation.

    Schema Version 2 format:
    - Issue body: metadata-only (schema_version, created_at, created_by, worktree_name)
    - First comment: plan content wrapped in markers
    """
    try:
        # Step 1: Check gh CLI availability
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            result = {"success": False, "error": "gh CLI not found or not working"}
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Step 2: Check gh authentication
        try:
            subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            result = {"success": False, "error": "gh CLI not authenticated - run 'gh auth login'"}
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Step 3: Get GitHub username
        username = _get_github_username()
        if username is None:
            result = {"success": False, "error": "Could not get GitHub username"}
            click.echo(json.dumps(result))
            raise SystemExit(1)

        # Step 4: Extract latest plan from session
        import os

        cwd = os.getcwd()
        plan_text = get_latest_plan(cwd, session_id)

        if not plan_text:
            result = {"success": False, "error": "No plan found in Claude session files"}
            click.echo(json.dumps(result))
            raise SystemExit(1)

        # Step 5: Extract base title from plan (without suffix)
        base_title = extract_title_from_plan(plan_text)

        # Generate timestamp
        created_at = datetime.now(UTC).isoformat()

        # Step 6: Ensure erk-plan label exists
        try:
            ensure_label_exists(
                label_name="erk-plan",
                label_color="0E8A16",
                label_description="Implementation plan for erk workflow",
            )
        except subprocess.CalledProcessError as e:
            result = {
                "success": False,
                "error": f"Failed to ensure label exists: {e.stderr if e.stderr else str(e)}",
            }
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Step 7: Format metadata-only body (schema version 2, worktree_name set later)
        formatted_body = format_plan_header_body(
            created_at=created_at,
            created_by=username,
        )

        # Step 8: Create GitHub issue with metadata body and [erk-plan] suffix
        issue_title = f"{base_title} [erk-plan]"
        try:
            create_result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    issue_title,
                    "--body",
                    formatted_body,
                    "--label",
                    "erk-plan",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse issue URL from output (gh returns URL on last line)
            issue_url = create_result.stdout.strip().split("\n")[-1]

            # Extract issue number from URL
            # URL format: https://github.com/owner/repo/issues/123
            issue_number = int(issue_url.rstrip("/").split("/")[-1])

        except subprocess.CalledProcessError as e:
            result = {
                "success": False,
                "error": f"Failed to create GitHub issue: {e.stderr if e.stderr else str(e)}",
            }
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Step 9: Add first comment with plan content
        plan_comment = format_plan_content_comment(plan_text.strip())
        try:
            subprocess.run(
                [
                    "gh",
                    "issue",
                    "comment",
                    str(issue_number),
                    "--body",
                    plan_comment,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            # Issue was created but comment failed - provide recovery info
            result = {
                "success": False,
                "error": (
                    f"Issue #{issue_number} created but failed to add plan comment: "
                    f"{e.stderr if e.stderr else str(e)}\n"
                    f"Please manually add plan content to: {issue_url}"
                ),
            }
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Return success result
        result = {
            "success": True,
            "issue_number": issue_number,
            "issue_url": issue_url,
            "title": issue_title,
        }
        click.echo(json.dumps(result))

    except SystemExit:
        raise
    except Exception as e:
        # Catch any unexpected errors
        result = {"success": False, "error": f"Unexpected error: {str(e)}"}
        click.echo(json.dumps(result))
        raise SystemExit(1) from None
