"""Extract plan from Claude session and save to disk.

Usage:
    dot-agent kit-command erk save-plan-from-session [--session-id SESSION_ID]

This command combines plan extraction from Claude session files with saving
to disk. It extracts the latest ExitPlanMode plan, generates a filename,
and saves it to the repository root with minimal frontmatter.

Output:
    JSON result on stdout: {"success": true, "file_path": "...", "title": "..."}
    Error messages on stderr with exit code 1 on failure

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


@click.command(name="save-plan-from-session")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
def save_plan_from_session(session_id: str | None) -> None:
    """Extract plan from Claude session and save to disk.

    Combines plan extraction with file saving in a single operation.
    """
    try:
        # Get current working directory
        cwd = Path.cwd()

        # Step 1: Extract latest plan from session
        plan_text = get_latest_plan(str(cwd), session_id)

        if not plan_text:
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
            result = {"success": False, "error": "Not in a git repository"}
            click.echo(json.dumps(result))
            raise SystemExit(1) from None

        # Step 5: Construct file path
        file_path = repo_root / filename

        # Check if file already exists
        if file_path.exists():
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
        result = {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "title": title,
            "timestamp": timestamp,
        }
        click.echo(json.dumps(result))

    except Exception as e:
        # Catch any unexpected errors
        result = {"success": False, "error": f"Unexpected error: {str(e)}"}
        click.echo(json.dumps(result))
        raise SystemExit(1) from None
