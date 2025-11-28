"""Mark a step as completed or incomplete in progress.md.

This kit CLI command updates the YAML frontmatter in .impl/progress.md to mark
a specific step as completed or incomplete, then regenerates the checkboxes.

Usage:
    dot-agent run erk mark-step STEP_NUM
    dot-agent run erk mark-step STEP_NUM --incomplete
    dot-agent run erk mark-step STEP_NUM --json

Output:
    JSON format: {"success": true, "step_num": N, "completed": true,
                  "total_completed": X, "total_steps": Y}
    Human format: ✓ Step N: <description>\n              Progress: X/Y

Exit Codes:
    0: Success
    1: Error (missing file, invalid step number, malformed YAML)

Examples:
    $ dot-agent run erk mark-step 5
    ✓ Step 5: Implement feature X
    Progress: 5/10

    $ dot-agent run erk mark-step 5 --json
    {"success": true, "step_num": 5, "completed": true, "total_completed": 5, "total_steps": 10}

    $ dot-agent run erk mark-step 5 --incomplete
    ○ Step 5: Implement feature X
    Progress: 4/10
"""

import json
from pathlib import Path
from typing import Any, NoReturn

import click
import frontmatter


def _error(msg: str) -> NoReturn:
    """Output error message and exit with code 1."""
    click.echo(f"❌ Error: {msg}", err=True)
    raise SystemExit(1)


def _validate_progress_file() -> Path:
    """Validate .impl/progress.md exists.

    Returns:
        Path to progress.md

    Raises:
        SystemExit: If validation fails
    """
    progress_file = Path.cwd() / ".impl" / "progress.md"

    if not progress_file.exists():
        _error("No progress.md found in .impl/ folder")

    return progress_file


def _parse_progress_file(progress_file: Path) -> tuple[dict[str, Any], str]:
    """Parse progress.md file and extract metadata and body.

    Args:
        progress_file: Path to progress.md

    Returns:
        Tuple of (metadata dict, body content)

    Raises:
        SystemExit: If YAML is malformed or missing required fields
    """
    content = progress_file.read_text(encoding="utf-8")

    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(content)
    except Exception as e:
        _error(f"Failed to parse YAML frontmatter: {e}")

    metadata = post.metadata

    # Validate required fields
    if "steps" not in metadata:
        _error("Progress file missing 'steps' array in frontmatter")

    if "total_steps" not in metadata:
        _error("Progress file missing 'total_steps' in frontmatter")

    if not isinstance(metadata["steps"], list):
        _error("'steps' field must be an array")

    return metadata, post.content


def _update_step_status(
    metadata: dict[str, Any],
    step_num: int,
    completed: bool,
) -> None:
    """Update step status in metadata and recalculate completed_steps count.

    Args:
        metadata: Progress metadata dict (modified in place)
        step_num: Step number (1-indexed)
        completed: True to mark complete, False for incomplete

    Raises:
        SystemExit: If step_num is out of range
    """
    total_steps = metadata["total_steps"]
    steps = metadata["steps"]

    if step_num < 1 or step_num > total_steps:
        _error(f"Step number {step_num} out of range (1-{total_steps})")

    # Update step status (convert to 0-indexed)
    steps[step_num - 1]["completed"] = completed

    # Recalculate completed_steps count
    completed_count = sum(1 for step in steps if step["completed"])
    metadata["completed_steps"] = completed_count


def _regenerate_checkboxes(steps: list[dict[str, Any]]) -> str:
    """Regenerate checkbox markdown from steps array.

    Args:
        steps: List of step dicts with 'text' and 'completed' fields

    Returns:
        Markdown body with checkboxes
    """
    lines = ["# Progress Tracking\n"]

    for step in steps:
        checkbox = "[x]" if step["completed"] else "[ ]"
        lines.append(f"- {checkbox} {step['text']}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)


def _write_progress_file(
    progress_file: Path,
    metadata: dict[str, Any],
) -> None:
    """Write updated progress.md file with new metadata and regenerated checkboxes.

    Args:
        progress_file: Path to progress.md
        metadata: Updated metadata dict
    """
    # Regenerate body from steps array
    body = _regenerate_checkboxes(metadata["steps"])

    # Create frontmatter post and write atomically
    post = frontmatter.Post(body, **metadata)
    content = frontmatter.dumps(post)
    progress_file.write_text(content, encoding="utf-8")


@click.command(name="mark-step")
@click.argument("step_num", type=int)
@click.option(
    "--completed/--incomplete",
    default=True,
    help="Mark as completed (default) or incomplete",
)
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
def mark_step(step_num: int, completed: bool, output_json: bool) -> None:
    """Mark a step as completed or incomplete in progress.md.

    Updates the YAML frontmatter to mark STEP_NUM as completed/incomplete,
    recalculates the completed_steps count, and regenerates checkboxes.

    STEP_NUM: Step number to mark (1-indexed)
    """
    progress_file = _validate_progress_file()
    metadata, _ = _parse_progress_file(progress_file)

    _update_step_status(metadata, step_num, completed)
    _write_progress_file(progress_file, metadata)

    # Output result
    if output_json:
        result = {
            "success": True,
            "step_num": step_num,
            "completed": completed,
            "total_completed": metadata["completed_steps"],
            "total_steps": metadata["total_steps"],
        }
        click.echo(json.dumps(result))
    else:
        # Get step text for human output
        step_text = metadata["steps"][step_num - 1]["text"]
        status_icon = "✓" if completed else "○"
        click.echo(f"{status_icon} Step {step_num}: {step_text}")
        click.echo(f"Progress: {metadata['completed_steps']}/{metadata['total_steps']}")
