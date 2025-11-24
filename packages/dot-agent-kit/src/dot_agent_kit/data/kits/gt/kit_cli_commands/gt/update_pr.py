"""Graphite update-pr workflow.

This module provides a streamlined version of the Graphite update-pr workflow.

Design goals:
- Fail fast with natural error messages
- Single linear execution flow
- No error categorization or state tracking
- Reuse existing RealGtKit operations
- Simple JSON output without complex types
"""

import json
import sys

import click

from erk.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKit


def execute_update_pr() -> dict:
    """Execute the update-pr workflow.

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    kit = RealGtKit()

    # 1. Check PR exists
    pr_info = kit.github().get_pr_info()
    if not pr_info:
        return {"success": False, "error": "No PR associated with current branch"}

    pr_number, pr_url = pr_info

    # 2. Commit if uncommitted changes
    if kit.git().has_uncommitted_changes():
        if not kit.git().add_all():
            return {"success": False, "error": "Failed to stage changes"}
        if not kit.git().commit("Update changes"):
            return {"success": False, "error": "Failed to commit changes"}

    # 3. Restack
    if not kit.graphite().restack():
        return {"success": False, "error": "Failed to restack branch"}

    # 4. Submit update
    result = kit.graphite().submit(publish=False, restack=False)
    if not result.success:
        return {"success": False, "error": f"Failed to submit update: {result.stderr}"}

    return {"success": True, "pr_number": pr_number, "pr_url": pr_url}


@click.command()
def update_pr() -> None:
    """Graphite update-pr workflow.

    Usage:
        dot-agent run gt update-pr
    """
    result = execute_update_pr()
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    update_pr()
