"""Extract plan from Claude session and save to disk.

Usage:
    dot-agent kit-command erk save-plan-from-session [--session-id SESSION_ID] [--format FORMAT]

This command combines plan extraction from Claude session files with saving
to disk. It extracts the latest ExitPlanMode plan, generates a filename,
and saves it to the repository root with minimal frontmatter.

Output:
    --format json (default): JSON result on stdout
    --format display: Formatted text ready for display

Error messages:
    --format json: JSON with "success": false and "error" field
    --format display: Formatted error messages to stderr

Exit Codes:
    0: Success - plan saved
    1: Error - no plan found, file exists, or other error
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click

from dot_agent_kit.data.kits.erk.plan_utils import (
    extract_title_from_plan,
    generate_filename_from_title,
)
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan


def _format_success_display(filename: str, title: str, file_path: Path) -> None:
    """Format and output success message for display mode."""
    click.echo(f"✅ Plan saved to: {filename}")
    click.echo()
    click.echo(f"📋 Title: {title}")
    click.echo(f"📁 Path: {file_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("1. Review the plan if needed")
    click.echo("2. Create worktree: /erk:create-wt-from-plan-file")
    click.echo("3. Switch to worktree and implement")


def _format_error_display(error_message: str, details: str | None = None) -> None:
    """Format and output error message for display mode."""
    click.echo(f"❌ Error: {error_message}", err=True)
    if details:
        click.echo(f"\nDetails: {details}", err=True)


@click.command(name="save-plan-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
def save_plan_from_session(session_id: str | None, output_format: str) -> None:
    """Extract plan from Claude session and save to disk.

    Combines plan extraction with file saving in a single operation.
    """
    # Get current working directory
    cwd = Path.cwd()

    # Step 1: Extract latest plan from session
    plan_text = get_latest_plan(str(cwd), session_id)

    if not plan_text:
        if output_format == "display":
            _format_error_display(
                "No plan found in Claude session files",
                "No ExitPlanMode tool uses found in session history",
            )
            click.echo("\nSuggested action:", err=True)
            click.echo(
                "1. Create a plan first (enter Plan mode, create plan, exit Plan mode)", err=True
            )
            click.echo("2. Ensure you exited Plan mode with ExitPlanMode tool", err=True)
            click.echo("3. Try again after creating a plan", err=True)
        else:
            result = {"success": False, "error": "No plan found in Claude session files"}
            click.echo(json.dumps(result))
        raise SystemExit(1)

    # Step 2: Extract title from plan
    title = extract_title_from_plan(plan_text)

    # Step 3: Generate filename
    filename = generate_filename_from_title(title)

    # Step 4: Get repository root
    try:
        repo_root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        )
        repo_root = Path(repo_root_result.stdout.strip())
    except subprocess.CalledProcessError:
        if output_format == "display":
            _format_error_display("Not in a git repository")
        else:
            result = {"success": False, "error": "Not in a git repository"}
            click.echo(json.dumps(result))
        raise SystemExit(1) from None

    # Step 5: Construct file path
    file_path = repo_root / filename

    # Check if file already exists
    if file_path.exists():
        if output_format == "display":
            _format_error_display(f"File already exists: {file_path}")
        else:
            result = {
                "success": False,
                "error": f"File already exists: {file_path}",
                "file_path": str(file_path),
            }
            click.echo(json.dumps(result))
        raise SystemExit(1)

    # Step 6: Add minimal frontmatter
    timestamp = datetime.now(UTC).isoformat()
    content = f"""---
erk_plan: true
created_at: {timestamp}
---

{plan_text}"""

    # Step 7: Write file
    file_path.write_text(content, encoding="utf-8")

    # Return success result
    if output_format == "display":
        _format_success_display(filename, title, file_path)
    else:
        result = {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "title": title,
            "timestamp": timestamp,
        }
        click.echo(json.dumps(result))
