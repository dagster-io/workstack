#!/usr/bin/env python3
"""Execute LibCST transformation code safely."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import click


@click.command()
@click.option(
    "--code",
    help="Python transformation code (fallback if stdin not provided)",
    default=None,
)
@click.option(
    "--files",
    required=True,
    help="File glob pattern for files to transform (e.g., 'src/**/*.py')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without writing files",
)
def execute(code: str | None, files: str, dry_run: bool) -> None:
    """Execute LibCST transformation code safely.

    Reads Python transformation code from stdin (preferred) or --code argument,
    executes it in an isolated subprocess, and returns JSON results.

    Examples:

        # Primary usage (stdin for large code)
        echo "$generated_code" | dot-agent run libcst:execute --files "src/**/*.py" --dry-run

        # Fallback (--code for testing)
        dot-agent run libcst:execute --code "print('test')" --files "test.py"
    """
    # Read code from stdin if available, otherwise use --code argument
    transformation_code: str | None = None

    # Try to read from stdin if it's not a TTY (i.e., piped input)
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
        # Only use stdin if it has non-whitespace content
        if stdin_data.strip():
            transformation_code = stdin_data

    # Fall back to --code argument if stdin didn't provide code
    if transformation_code is None:
        transformation_code = code

    # Check if we have any code at all
    has_empty_code = transformation_code is None or (
        isinstance(transformation_code, str) and not transformation_code.strip()
    )
    if has_empty_code:
        # Determine which error message to show
        if code is not None and not code.strip():
            # Code was explicitly provided but is empty/whitespace
            error_msg = "Transformation code is empty"
        else:
            # No code was provided at all
            error_msg = "No transformation code provided via stdin or --code argument"

        result = {
            "success": False,
            "files_modified": [],
            "changes_count": 0,
            "errors": [error_msg],
        }
        click.echo(json.dumps(result), err=True)
        raise SystemExit(1)

    # At this point, transformation_code is guaranteed to be a non-empty string
    # (the check above ensures it's not None and not empty)
    assert isinstance(transformation_code, str)

    # Execute transformation in isolated subprocess
    try:
        result_data = _execute_transformation(transformation_code, files, dry_run)
        click.echo(json.dumps(result_data))

        if not result_data["success"]:
            raise SystemExit(1)

    except Exception as e:
        result = {
            "success": False,
            "files_modified": [],
            "changes_count": 0,
            "errors": [f"Unexpected error: {e}"],
        }
        click.echo(json.dumps(result), err=True)
        raise SystemExit(1) from None


def _execute_transformation(code: str, files_pattern: str, dry_run: bool) -> dict[str, Any]:
    """Execute transformation code in subprocess and return structured result.

    Args:
        code: Python transformation code to execute
        files_pattern: File glob pattern for target files
        dry_run: Whether to run in preview mode

    Returns:
        Dictionary with keys: success, files_modified, changes_count, errors
    """
    # Write transformation code to temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_script_path = Path(temp_file.name)
        temp_file.write(code)

    try:
        # Prepare environment with DRY_RUN flag if needed
        env = os.environ.copy()
        if dry_run:
            env["DRY_RUN"] = "1"

        # Execute transformation script
        result = subprocess.run(
            [sys.executable, str(temp_script_path), files_pattern],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        # Parse JSON output from transformation script
        try:
            output_data = json.loads(result.stdout)
            return output_data
        except json.JSONDecodeError:
            # If output is not JSON, return as preview text
            return {
                "success": True,
                "files_modified": [],
                "changes_count": 0,
                "preview": result.stdout,
                "errors": [],
            }

    except subprocess.CalledProcessError as e:
        # Transformation script failed
        error_message = e.stderr if e.stderr else str(e)

        # Try to parse JSON error from script
        try:
            error_data = json.loads(e.stderr)
            return error_data
        except (json.JSONDecodeError, ValueError):
            pass

        # Return structured error
        return {
            "success": False,
            "files_modified": [],
            "changes_count": 0,
            "errors": [f"Transformation failed: {error_message}"],
        }

    finally:
        # Clean up temporary script file
        if temp_script_path.exists():
            temp_script_path.unlink()


if __name__ == "__main__":
    execute()
