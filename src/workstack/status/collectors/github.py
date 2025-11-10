"""GitHub PR collector."""

from pathlib import Path

from workstack.core.context import WorkstackContext
from workstack.status.collectors.base import StatusCollector
from workstack.status.models.status_data import PullRequestStatus


class GitHubPRCollector(StatusCollector):
    """Collects GitHub pull request information."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "pr"

    def is_available(self, ctx: WorkstackContext, worktree_path: Path) -> bool:
        """Check if PR information should be fetched.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree

        Returns:
            True if PR info is enabled in config
        """
        if not (ctx.global_config and ctx.global_config.show_pr_info):
            return False

        if not worktree_path.exists():
            return False

        return True

    def collect(
        self, ctx: WorkstackContext, worktree_path: Path, repo_root: Path
    ) -> PullRequestStatus | None:
        """Collect GitHub PR information.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PullRequestStatus with PR information or None if collection fails
        """
        branch = ctx.git_ops.get_current_branch(worktree_path)
        if branch is None:
            return None

        # Try Graphite first (fast - no CI status)
        prs = ctx.graphite_ops.get_prs_from_graphite(ctx.git_ops, repo_root)

        # If Graphite data not available, fall back to GitHub
        if not prs:
            prs = ctx.github_ops.get_prs_for_repo(repo_root, include_checks=True)

        # Find PR for current branch
        pr = prs.get(branch)
        if pr is None:
            return None

        # Determine if ready to merge
        ready_to_merge = (
            pr.state == "OPEN"
            and not pr.is_draft
            and (pr.checks_passing is True or pr.checks_passing is None)
        )

        return PullRequestStatus(
            number=pr.number,
            title=None,  # Title not available in PullRequestInfo
            state=pr.state,
            is_draft=pr.is_draft,
            url=pr.url,
            checks_passing=pr.checks_passing,
            reviews=None,  # Reviews not available in PullRequestInfo
            ready_to_merge=ready_to_merge,
        )
