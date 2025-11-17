"""Status command implementation."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.json_output import json_error_boundary
from erk.cli.output import user_output
from erk.cli.rendering import get_renderer
from erk.core.context import ErkContext
from erk.core.parallel_task_runner import RealParallelTaskRunner
from erk.status.collectors.git import GitStatusCollector
from erk.status.collectors.github import GitHubPRCollector
from erk.status.collectors.graphite import GraphiteStackCollector
from erk.status.collectors.plan import PlanFileCollector
from erk.status.orchestrator import StatusOrchestrator


@click.command("status")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (text or json)",
)
@json_error_boundary
@click.pass_obj
def status_cmd(ctx: ErkContext, format: str) -> None:
    """Show comprehensive status of current worktree.

    \b
    JSON Output (--format json):
    Output schema is defined and validated by StatusCommandResponse
    in erk.cli.json_schemas. The Pydantic model ensures type safety
    and runtime validation of the JSON structure.
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    current_dir = ctx.cwd.resolve()

    # Find which worktree we're in
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    current_worktree_path = None

    for wt in worktrees:
        # Check path exists before resolution/comparison to avoid OSError
        if wt.path.exists():
            wt_path_resolved = wt.path.resolve()
            # Use is_relative_to only after confirming path exists
            if current_dir == wt_path_resolved or current_dir.is_relative_to(wt_path_resolved):
                current_worktree_path = wt_path_resolved
                break

    if current_worktree_path is None:
        user_output("Error: Not in a git worktree")
        raise SystemExit(1)

    # Create collectors
    collectors = [
        GitStatusCollector(),
        GraphiteStackCollector(),
        GitHubPRCollector(),
        PlanFileCollector(),
    ]

    # Create orchestrator
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Collect status
    status = orchestrator.collect_status(ctx, current_worktree_path, repo.root)

    # Render status with appropriate renderer
    renderer = get_renderer(format)
    renderer.render_status(status)
