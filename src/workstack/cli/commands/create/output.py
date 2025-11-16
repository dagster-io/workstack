"""Output formatting for the create command.

This module handles all output formatting for the create command,
including script generation, JSON output, and human-readable messages.
"""

import json
from pathlib import Path

import click

from workstack.cli.output import user_output
from workstack.cli.shell_utils import render_cd_script
from workstack.core.context import WorkstackContext

from .types import BranchConfig, CreateVariant, OutputConfig, WorktreeTarget


def output_result(
    config: OutputConfig,
    ctx: WorkstackContext,
    target: WorktreeTarget,
    branch_config: BranchConfig,
    variant: CreateVariant,
    plan_dest: Path | None,
    source_name: str | None,
) -> None:
    """Output results based on mode.

    Handles three output modes:
    - script: Generate shell activation script for directory change
    - json: Emit JSON with worktree information
    - human: Display human-readable success message

    Args:
        config: Output configuration
        ctx: Workstack context
        target: Worktree target configuration
        branch_config: Branch configuration used
        variant: Which variant was used
        plan_dest: Plan destination path (for plan variant)
        source_name: Source workstack name (for with_dot_plan variant)
    """
    if config.mode == "script" and not config.stay:
        _output_script(ctx, target)
    elif config.mode == "json":
        _output_json(target, branch_config, plan_dest)
    else:
        _output_human(target, branch_config, variant, source_name)


def _output_script(ctx: WorkstackContext, target: WorktreeTarget) -> None:
    """Generate shell activation script for directory change.

    Args:
        ctx: Workstack context with script writer
        target: Worktree target configuration
    """
    script_content = render_cd_script(
        target.path,
        comment="cd to new worktree",
        success_message="✓ Switched to new worktree.",
    )
    result = ctx.script_writer.write_activation_script(
        script_content,
        command_name="create",
        comment=f"cd to {target.name}",
    )
    result.output_for_shell_integration()


def _output_json(
    target: WorktreeTarget,
    branch_config: BranchConfig,
    plan_dest: Path | None,
) -> None:
    """Emit JSON with worktree information.

    Args:
        target: Worktree target configuration
        branch_config: Branch configuration used
        plan_dest: Plan destination path if applicable
    """
    json_response = create_json_response(
        worktree_name=target.name,
        worktree_path=target.path,
        branch_name=branch_config.branch,
        plan_file_path=plan_dest,
        status="created",
    )
    user_output(json_response)


def _output_human(
    target: WorktreeTarget,
    branch_config: BranchConfig,
    variant: CreateVariant,
    source_name: str | None,
) -> None:
    """Display human-readable success message.

    The with_dot_plan variant gets special formatting to show
    the sibling relationship.

    Args:
        target: Worktree target configuration
        branch_config: Branch configuration used
        variant: Which variant was used
        source_name: Source workstack name for with_dot_plan variant
    """
    if variant == "with_dot_plan" and source_name:
        # Special output for with_dot_plan variant
        user_output("")
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree based on {click.style(branch_config.ref, fg='yellow')}"
        )
        branch_styled = click.style(branch_config.branch, fg="yellow")
        source_branch = click.style(source_name, fg="yellow")
        user_output(
            click.style("✓", fg="green")
            + f" New branch {branch_styled} is sibling to {source_branch}"
        )
        user_output("")
        user_output(f"Worktree path: {click.style(str(target.path), fg='green')}")
        user_output(f"\nworkstack switch {target.name}")
    else:
        # Standard output for all other variants
        user_output(
            f"Created workstack at {target.path} checked out at branch '{branch_config.branch}'"
        )
        user_output(f"\nworkstack switch {target.name}")


def create_json_response(
    *,
    worktree_name: str,
    worktree_path: Path,
    branch_name: str | None,
    plan_file_path: Path | None,
    status: str,
) -> str:
    """Generate JSON response for create command.

    Args:
        worktree_name: Name of the worktree
        worktree_path: Path to the worktree directory
        branch_name: Git branch name (may be None if not available)
        plan_file_path: Path to plan file if exists, None otherwise
        status: Status string ("created" or "exists")

    Returns:
        JSON string with worktree information
    """
    return json.dumps(
        {
            "worktree_name": worktree_name,
            "worktree_path": str(worktree_path),
            "branch_name": branch_name,
            "plan_file": str(plan_file_path) if plan_file_path else None,
            "status": status,
        }
    )
