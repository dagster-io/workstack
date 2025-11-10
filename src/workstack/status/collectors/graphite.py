"""Graphite stack collector."""

from pathlib import Path

from workstack.core.context import GlobalConfigNotFound, WorkstackContext
from workstack.status.collectors.base import StatusCollector
from workstack.status.models.status_data import StackPosition


class GraphiteStackCollector(StatusCollector):
    """Collects Graphite stack position information."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "stack"

    def is_available(self, ctx: WorkstackContext, worktree_path: Path) -> bool:
        """Check if Graphite is enabled and available.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree

        Returns:
            True if Graphite is enabled
        """
        if isinstance(ctx.global_config, GlobalConfigNotFound):
            return False

        if not ctx.global_config.use_graphite:
            return False

        if not worktree_path.exists():
            return False

        return True

    def collect(
        self, ctx: WorkstackContext, worktree_path: Path, repo_root: Path
    ) -> StackPosition | None:
        """Collect Graphite stack information.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            StackPosition with stack information or None if collection fails
        """
        branch = ctx.git_ops.get_current_branch(worktree_path)
        if branch is None:
            return None

        # Get the stack for current branch
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, branch)
        if stack is None:
            return None

        # Find current branch position in stack
        if branch not in stack:
            return None

        current_idx = stack.index(branch)

        # Determine parent and children
        parent_branch = stack[current_idx - 1] if current_idx > 0 else None

        children_branches = []
        if current_idx < len(stack) - 1:
            children_branches.append(stack[current_idx + 1])

        # Check if this is trunk
        is_trunk = current_idx == 0

        return StackPosition(
            stack=stack,
            current_branch=branch,
            parent_branch=parent_branch,
            children_branches=children_branches,
            is_trunk=is_trunk,
        )
