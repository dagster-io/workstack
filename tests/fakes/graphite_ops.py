"""Fake Graphite operations for testing.

FakeGraphiteOps is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

from workstack.core.branch_metadata import BranchMetadata
from workstack.core.github_ops import PullRequestInfo
from workstack.core.gitops import GitOps
from workstack.core.graphite_ops import GraphiteOps


class FakeGraphiteOps(GraphiteOps):
    """In-memory fake implementation of Graphite operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).
    """

    def __init__(
        self,
        *,
        sync_raises: Exception | None = None,
        pr_info: dict[str, PullRequestInfo] | None = None,
        branches: dict[str, BranchMetadata] | None = None,
        stacks: dict[str, list[str]] | None = None,
    ) -> None:
        """Create FakeGraphiteOps with pre-configured state.

        Args:
            sync_raises: Exception to raise when sync() is called (for testing error cases)
            pr_info: Mapping of branch name -> PullRequestInfo for get_prs_from_graphite()
            branches: Mapping of branch name -> BranchMetadata for get_all_branches()
            stacks: Mapping of branch name -> stack (list of branches from trunk to leaf)
        """
        self._sync_raises = sync_raises
        self._sync_calls: list[tuple[Path, bool]] = []
        self._pr_info = pr_info if pr_info is not None else {}
        self._branches = branches if branches is not None else {}
        self._stacks = stacks if stacks is not None else {}

    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL (constructs URL directly)."""
        return f"https://app.graphite.dev/github/pr/{owner}/{repo}/{pr_number}"

    def sync(self, repo_root: Path, *, force: bool) -> None:
        """Fake sync operation.

        Tracks calls for verification and raises configured exception if set.
        """
        self._sync_calls.append((repo_root, force))

        if self._sync_raises is not None:
            raise self._sync_raises

    def get_prs_from_graphite(self, git_ops: GitOps, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Return pre-configured PR info for tests."""
        return self._pr_info.copy()

    def get_all_branches(self, git_ops: GitOps, repo_root: Path) -> dict[str, BranchMetadata]:
        """Return pre-configured branch metadata for tests."""
        return self._branches.copy()

    def get_branch_stack(self, git_ops: GitOps, repo_root: Path, branch: str) -> list[str] | None:
        """Return pre-configured stack for the given branch."""
        # If stacks are configured, use those
        if self._stacks:
            # Find the stack that contains this branch
            for _stack_branch, stack in self._stacks.items():
                if branch in stack:
                    return stack.copy()
            return None

        # Otherwise, build from branch metadata if available
        if not self._branches:
            return None

        if branch not in self._branches:
            return None

        # Build stack from branch metadata (simplified version)
        ancestors: list[str] = []
        current = branch
        while current in self._branches:
            ancestors.append(current)
            parent = self._branches[current].parent
            if parent is None or parent not in self._branches:
                break
            current = parent

        ancestors.reverse()

        # Add descendants
        descendants: list[str] = []
        current = branch
        while current in self._branches:
            children = self._branches[current].children
            if not children:
                break
            first_child = children[0]
            if first_child not in self._branches:
                break
            descendants.append(first_child)
            current = first_child

        return ancestors + descendants

    @property
    def sync_calls(self) -> list[tuple[Path, bool]]:
        """Get the list of sync() calls that were made.

        Returns list of (repo_root, force) tuples.

        This property is for test assertions only.
        """
        return self._sync_calls
