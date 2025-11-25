"""Command to close a plan."""

from urllib.parse import urlparse

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


@click.command("close")
@click.argument("identifier", type=str)
@click.pass_obj
def close_plan(ctx: ErkContext, identifier: str) -> None:
    """Close a plan by issue number or GitHub URL.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    try:
        ctx.plan_store.close_plan(repo_root, identifier)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Extract issue number for output
    # Try to extract from identifier (either numeric or URL)
    if identifier.isdigit():
        number = identifier
    else:
        # Security: Use proper URL parsing to validate hostname
        parsed = urlparse(identifier)
        if parsed.hostname == "github.com" and parsed.path:
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 2 and parts[-2] == "issues":
                number = parts[-1]
            else:
                number = identifier  # Fallback to showing identifier as-is
        else:
            number = identifier  # Fallback to showing identifier as-is

    user_output(f"Closed plan #{number}")
