"""Status command implementation."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import WorkstackContext
from erk.core.parallel_task_runner import RealParallelTaskRunner
from erk.status.collectors.git import GitStatusCollector
from erk.status.collectors.github import GitHubPRCollector
from erk.status.collectors.graphite import GraphiteStackCollector
from erk.status.collectors.plan import PlanFileCollector
from erk.status.orchestrator import StatusOrchestrator
from erk.status.renderers.simple import SimpleRenderer


@click.command("status")
@click.pass_obj
def status_cmd(ctx: WorkstackContext) -> None:
    """Show comprehensive status of current worktree."""
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

    # Render status
    renderer = SimpleRenderer()
    renderer.render(status)
