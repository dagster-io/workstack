"""Extract plan from Claude session and optionally save to disk.

Usage:
    # Extract and save to disk
    dot-agent run erk save-plan-from-session [--session-id SESSION_ID] [--format FORMAT]

    # Extract only (no disk write)
    dot-agent run erk save-plan-from-session --extract-only [--session-id ID] [--format FMT]

This command extracts the latest ExitPlanMode plan from Claude session files.
Without --extract-only, it saves to disk. With --extract-only, it returns
the plan content in JSON without saving (useful for agent orchestration).

Session ID Discovery:
    1. Use explicit --session-id if provided
    2. Otherwise discover from SESSION_CONTEXT environment (session_id=<uuid>)
    3. Fall back to CLAUDE_SESSION_ID environment
    4. If none found, searches all session files

Output:
    --format json (default): JSON result on stdout
    --format display: Formatted text ready for display

Error messages:
    --format json: JSON with "success": false and "error" field
    --format display: Formatted error messages to stderr

Exit Codes:
    0: Success - plan extracted (and saved if not --extract-only)
    1: Error - no plan found, file exists, or other error
"""

import json
import subprocess
from pathlib import Path

import click
from erk_shared.naming import generate_filename_from_title

from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan, get_session_context


def _format_success_display(filename: str, title: str, file_path: Path) -> None:
    """Format and output success message for display mode."""
    click.echo(f"✅ Plan saved to: {filename}")
    click.echo()
    click.echo(f"📋 Title: {title}")
    click.echo(f"📁 Path: {file_path}")
    click.echo()
    click.echo("Next steps:")
    click.echo("1. Review the plan if needed")
    click.echo("2. Create worktree: erk implement <issue>")
    click.echo("3. Implementation will execute automatically")


def _format_error_display(error_message: str, details: str | None = None) -> None:
    """Format and output error message for display mode."""
    click.echo(f"❌ Error: {error_message}", err=True)
    if details:
        click.echo(f"\nDetails: {details}", err=True)


@click.command(name="plan-save-from-session")
@click.option(
    "--session-id",
    help="Session ID to search (optional, auto-discovered from SESSION_CONTEXT or searches all)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--extract-only",
    is_flag=True,
    help="Extract plan without saving to disk (returns plan_content in JSON)",
)
def save_plan_from_session(session_id: str | None, output_format: str, extract_only: bool) -> None:
    """Extract plan from Claude session and save to disk.

    Combines plan extraction with file saving in a single operation.
    With --extract-only, returns plan content without saving.
    """
    # Get current working directory
    cwd = Path.cwd()

    # If session_id not provided, try to discover from environment
    if not session_id:
        session_id = get_session_context()

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

    # If extract-only mode, return plan content and exit
    if extract_only:
        if output_format == "display":
            click.echo(f"📋 Title: {title}")
            click.echo()
            click.echo(plan_text)
        else:
            result = {
                "success": True,
                "plan_content": plan_text,
                "title": title,
            }
            click.echo(json.dumps(result))
        return

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

    # Step 6: Write file (no frontmatter generation)
    content = plan_text
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
        }
        click.echo(json.dumps(result))
