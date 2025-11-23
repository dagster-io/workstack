"""Extract plan from Claude session and create GitHub issue.

Usage:
    dot-agent kit-command erk create-issue-from-session [--session-id SESSION_ID]

This command combines plan extraction from Claude session files with GitHub
issue creation. It extracts the latest ExitPlanMode plan, ensures the erk-plan
label exists, and creates a GitHub issue with the plan content.

Output:
    JSON result on stdout: {"success": true, "issue_number": N, "issue_url": "..."}
    Error messages on stderr with exit code 1 on failure

Exit Codes:
    0: Success - issue created
    1: Error - no plan found, gh CLI not available, or other error
"""

import json
import subprocess

import click

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


@click.command(name="create-issue-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
def create_issue_from_session(session_id: str | None) -> None:
    """Extract plan from Claude session and create GitHub issue.

    Combines plan extraction with GitHub issue creation in a single operation.
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

        # Step 3: Extract latest plan from session
        import os

        cwd = os.getcwd()
        plan_text = get_latest_plan(cwd, session_id)

        if not plan_text:
            result = {"success": False, "error": "No plan found in Claude session files"}
            click.echo(json.dumps(result))
            raise SystemExit(1)

        # Step 4: Extract title from plan
        title = extract_title_from_plan(plan_text)

        # Step 5: Ensure erk-plan label exists
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

        # Step 6: Create GitHub issue
        try:
            # Create issue with plan as body
            create_result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    title,
                    "--body",
                    plan_text,
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

            # Return success result
            result = {
                "success": True,
                "issue_number": issue_number,
                "issue_url": issue_url,
                "title": title,
            }
            click.echo(json.dumps(result))

        except subprocess.CalledProcessError as e:
            result = {
                "success": False,
                "error": f"Failed to create GitHub issue: {e.stderr if e.stderr else str(e)}",
            }
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

    except Exception as e:
        # Catch any unexpected errors
        result = {"success": False, "error": f"Unexpected error: {str(e)}"}
        click.echo(json.dumps(result))
        raise SystemExit(1) from None
