"""Status command implementation."""

from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext
from workstack.core.parallel_task_runner import RealParallelTaskRunner
from workstack.status.collectors.git import GitStatusCollector
from workstack.status.collectors.github import GitHubPRCollector
from workstack.status.collectors.graphite import GraphiteStackCollector
from workstack.status.collectors.plan import PlanFileCollector
from workstack.status.orchestrator import StatusOrchestrator
from workstack.status.renderers.simple import SimpleRenderer


@click.command("status")
@click.pass_obj
def status_cmd(ctx: WorkstackContext) -> None:
    """Show comprehensive status of current worktree."""
    # Discover repository context
    repo = discover_repo_context(ctx, Path.cwd())
    current_dir = Path.cwd().resolve()

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
        click.echo("Error: Not in a git worktree", err=True)
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
