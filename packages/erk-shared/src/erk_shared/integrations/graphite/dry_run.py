"""No-op wrapper for Graphite operations."""

from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.types import BranchMetadata, CommandResult


class DryRunGraphite(Graphite):
    """No-op wrapper that prevents execution of destructive operations.

    This wrapper intercepts destructive graphite operations and returns without
    executing (no-op behavior). Read-only operations are delegated to the wrapped implementation.

    Usage:
        real_ops = RealGraphite()
        noop_ops = DryRunGraphite(real_ops)

        # No-op instead of running gt sync
        noop_ops.sync(repo_root, force=False)
    """

    def __init__(self, wrapped: Graphite) -> None:
        """Create a dry-run wrapper around a Graphite implementation.

        Args:
            wrapped: The Graphite implementation to wrap (usually RealGraphite)
        """
        self._wrapped = wrapped

    # Read-only operations: delegate to wrapped implementation

    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL (read-only, delegates to wrapped)."""
        return self._wrapped.get_graphite_url(owner, repo, pr_number)

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR info from Graphite cache (read-only, delegates to wrapped)."""
        return self._wrapped.get_prs_from_graphite(git_ops, repo_root)

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all branches metadata (read-only, delegates to wrapped)."""
        return self._wrapped.get_all_branches(git_ops, repo_root)

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Get branch stack (read-only operation, delegates to wrapped)."""
        return self._wrapped.get_branch_stack(git_ops, repo_root, branch)

    # Destructive operations: print dry-run message instead of executing

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """No-op for gt sync in dry-run mode."""
        # Do nothing - prevents actual gt sync execution
        pass

    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """No-op for gt restack in dry-run mode."""
        # Do nothing - prevents actual gt restack execution
        pass

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """No-op for gt track in dry-run mode."""
        # Do nothing - prevents actual gt track execution
        pass

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """No-op for gt submit in dry-run mode."""
        # Do nothing - prevents actual gt submit execution
        pass

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check authentication status (read-only, delegates to wrapped)."""
        return self._wrapped.check_auth_status()

    def restack_with_result(self, repo_root: Path) -> CommandResult:
        """No-op for gt restack in dry-run mode, returns success."""
        # Return success without executing - dry-run mode
        return CommandResult(success=True, stdout="", stderr="")

    def squash_commits(self, repo_root: Path) -> CommandResult:
        """No-op for gt squash in dry-run mode, returns success."""
        # Return success without executing - dry-run mode
        return CommandResult(success=True, stdout="", stderr="")

    def submit(self, repo_root: Path, *, publish: bool, restack: bool) -> CommandResult:
        """No-op for gt submit in dry-run mode, returns success."""
        # Return success without executing - dry-run mode
        return CommandResult(success=True, stdout="", stderr="")

    def navigate_to_child(self, repo_root: Path) -> bool:
        """No-op for gt up in dry-run mode, returns success."""
        # Return success without executing - dry-run mode
        return True
