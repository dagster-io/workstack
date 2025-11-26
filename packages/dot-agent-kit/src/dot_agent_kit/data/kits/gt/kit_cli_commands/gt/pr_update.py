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

from erk.data.kits.gt.kit_cli_commands.gt.ops import GtKit
from erk.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKit


def execute_update_pr(ops: GtKit | None = None) -> dict:
    """Execute the update-pr workflow.

    Args:
        ops: Optional GtKit operations interface. Defaults to RealGtKit().

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    if ops is None:
        ops = RealGtKit()

    # 1. Commit if uncommitted changes
    if ops.git().has_uncommitted_changes():
        if not ops.git().add_all():
            return {"success": False, "error": "Failed to stage changes"}
        if not ops.git().commit("Update changes"):
            return {"success": False, "error": "Failed to commit changes"}

    # 2. Restack with conflict detection
    restack_result = ops.graphite().restack()
    if not restack_result.success:
        combined_output = restack_result.stdout + restack_result.stderr
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return {
                "success": False,
                "error_type": "restack_conflict",
                "error": (
                    "Merge conflict detected during restack. "
                    "Resolve conflicts manually or run 'gt restack --continue' after fixing."
                ),
                "details": {"stderr": restack_result.stderr},
            }

        return {
            "success": False,
            "error_type": "restack_failed",
            "error": "Failed to restack branch",
            "details": {"stderr": restack_result.stderr},
        }

    # 3. Submit update
    result = ops.graphite().submit(publish=True, restack=False)
    if not result.success:
        return {"success": False, "error": f"Failed to submit update: {result.stderr}"}

    # 4. Fetch PR info after submission
    pr_info = ops.github().get_pr_info()
    if not pr_info:
        return {"success": False, "error": "PR submission succeeded but failed to retrieve PR info"}

    pr_number, pr_url = pr_info

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
