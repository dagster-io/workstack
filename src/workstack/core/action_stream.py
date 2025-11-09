"""Stream-based dry-run architecture for declarative action execution.

This module provides a type-safe builder pattern for defining actions that can
be executed in production or previewed in dry-run mode. Replaces scattered
if/else dry-run checks with a single abstraction.

Example:
    >>> from workstack.core.action_stream import Action, ProductionStream, DryRunStream
    >>>
    >>> # Build actions using type-safe static builders
    >>> stream = DryRunStream(ctx) if dry_run else ProductionStream(ctx)
    >>> actions = [
    ...     Action.git_checkout(ctx, repo_root, "main"),
    ...     Action.subprocess_run("merge PR", ["gh", "pr", "merge", "123"], repo_root),
    ...     Action.graphite_sync(ctx, repo_root, force=True),
    ... ]
    >>> stream.run(actions)
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import click

from workstack.core.context import WorkstackContext


@dataclass(frozen=True)
class Action:
    """Declarative action that can be executed or previewed.

    Actions are created using static builder methods for type safety.
    Each action has a description for dry-run output and an executor
    function that performs the actual work in production mode.

    Args:
        description: Human-readable description of what this action does
        executor: Function that performs the action (called in production mode only)
        result_key: Optional key to store result in ActionStream.results for later access
    """

    description: str
    executor: Callable[[], object]
    result_key: str | None = None

    @staticmethod
    def git_checkout(ctx: WorkstackContext, repo_root: Path, branch: str) -> "Action":
        """Create action to checkout a git branch.

        Args:
            ctx: WorkstackContext with access to git operations
            repo_root: Repository root directory
            branch: Branch name to checkout

        Returns:
            Action that will checkout the specified branch
        """
        return Action(
            description=f"Checkout branch: {branch}",
            executor=lambda: ctx.git_ops.checkout_branch(repo_root, branch),
        )

    @staticmethod
    def git_add_worktree(
        ctx: WorkstackContext, repo_root: Path, worktree_path: Path, branch: str
    ) -> "Action":
        """Create action to add a git worktree.

        Args:
            ctx: WorkstackContext with access to git operations
            repo_root: Repository root directory
            worktree_path: Path where worktree should be created
            branch: Branch to checkout in the worktree

        Returns:
            Action that will add the specified worktree
        """
        return Action(
            description=f"Add worktree at {worktree_path} for branch {branch}",
            executor=lambda: ctx.git_ops.add_worktree(
                repo_root, worktree_path, branch=branch, ref=None, create_branch=False
            ),
        )

    @staticmethod
    def git_remove_worktree(
        ctx: WorkstackContext, repo_root: Path, worktree_path: Path
    ) -> "Action":
        """Create action to remove a git worktree.

        Args:
            ctx: WorkstackContext with access to git operations
            repo_root: Repository root directory
            worktree_path: Path to worktree to remove

        Returns:
            Action that will remove the specified worktree
        """
        return Action(
            description=f"Remove worktree at {worktree_path}",
            executor=lambda: ctx.git_ops.remove_worktree(repo_root, worktree_path, force=False),
        )

    @staticmethod
    def subprocess_run(description: str, cmd: list[str], cwd: Path) -> "Action":
        """Create action to run a subprocess command.

        Args:
            description: Human-readable description of what command does
            cmd: Command and arguments to execute
            cwd: Working directory for command execution

        Returns:
            Action that will execute the specified command
        """
        import subprocess

        def _executor() -> subprocess.CompletedProcess[str]:
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)

        return Action(
            description=description,
            executor=_executor,
        )

    @staticmethod
    def graphite_sync(
        ctx: WorkstackContext, repo_root: Path, *, force: bool, quiet: bool = True
    ) -> "Action":
        """Create action to run Graphite sync.

        Args:
            ctx: WorkstackContext with access to graphite operations
            repo_root: Repository root directory
            force: If True, force sync even with uncommitted changes
            quiet: If True, suppress graphite output

        Returns:
            Action that will run graphite sync
        """
        return Action(
            description=f"Run graphite sync (force={force}, quiet={quiet})",
            executor=lambda: ctx.graphite_ops.sync(repo_root, force=force, quiet=quiet),
        )

    @staticmethod
    def with_result(description: str, executor: Callable[[], object], result_key: str) -> "Action":
        """Create action that stores its result for later access.

        Use this when you need to access the result of an action in a later action.
        The result will be stored in ActionStream.results[result_key] after execution.

        Args:
            description: Human-readable description of what action does
            executor: Function that performs the action and returns a result
            result_key: Key to store result in ActionStream.results

        Returns:
            Action that will execute and store its result

        Example:
            >>> actions = [
            ...     Action.with_result(
            ...         "Get parent branch",
            ...         lambda: ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo_root, branch),
            ...         result_key="parent_branch"
            ...     ),
            ...     # Later action can access stream.results["parent_branch"]
            ... ]
        """
        return Action(description=description, executor=executor, result_key=result_key)


class ActionStream(ABC):
    """Abstract base for executing or previewing actions.

    Concrete implementations determine whether actions are executed
    (ProductionStream) or just previewed (DryRunStream).

    Attributes:
        ctx: WorkstackContext with access to operations
        verbose: Whether to show detailed output
        results: Dictionary storing results from actions with result_key set
    """

    def __init__(self, ctx: WorkstackContext, verbose: bool = False) -> None:
        """Initialize action stream.

        Args:
            ctx: WorkstackContext with access to operations
            verbose: Whether to show detailed output for operations
        """
        self.ctx = ctx
        self.verbose = verbose
        self.results: dict[str, object] = {}

    @abstractmethod
    def execute(self, action: Action) -> object | None:
        """Execute or preview a single action.

        Args:
            action: Action to execute or preview

        Returns:
            Result from executor (ProductionStream) or None (DryRunStream)
        """
        ...

    def run(self, actions: list[Action]) -> None:
        """Run all actions in sequence.

        For each action:
        - Call execute() to run or preview
        - If action has result_key, store result in self.results

        Args:
            actions: List of actions to run in order
        """
        for action in actions:
            result = self.execute(action)
            if action.result_key is not None:
                self.results[action.result_key] = result


class ProductionStream(ActionStream):
    """Production implementation that executes actions."""

    def execute(self, action: Action) -> object | None:
        """Execute action by calling its executor function.

        Args:
            action: Action to execute

        Returns:
            Result from executor function
        """
        return action.executor()


class DryRunStream(ActionStream):
    """Dry-run implementation that previews actions without executing."""

    def execute(self, action: Action) -> None:
        """Preview action by printing styled description.

        Args:
            action: Action to preview
        """
        dry_run_prefix = click.style("(dry run)", fg="bright_black")
        click.echo(f"  {dry_run_prefix} Would: {action.description}")
        return None
