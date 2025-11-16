"""Plan file collector."""

from pathlib import Path

from erk.core.context import WorkstackContext
from erk.core.plan_folder import get_plan_path, get_progress_path
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PlanStatus


class PlanFileCollector(StatusCollector):
    """Collects information about .plan/ folder."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "plan"

    def is_available(self, ctx: WorkstackContext, worktree_path: Path) -> bool:
        """Check if .plan/plan.md exists.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree

        Returns:
            True if .plan/plan.md exists
        """
        plan_path = get_plan_path(worktree_path, git_ops=ctx.git_ops)
        return plan_path is not None

    def collect(
        self, ctx: WorkstackContext, worktree_path: Path, repo_root: Path
    ) -> PlanStatus | None:
        """Collect plan folder information.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PlanStatus with folder information or None if collection fails
        """
        plan_path = get_plan_path(worktree_path, git_ops=ctx.git_ops)

        if plan_path is None:
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
                progress_summary=None,
                format="none",
            )

        # Read plan.md
        content = plan_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        line_count = len(lines)

        # Get first 5 lines
        first_lines = lines[:5] if len(lines) >= 5 else lines

        # Extract summary from first few non-empty lines
        summary_lines = []
        for line in lines[:10]:  # Look at first 10 lines
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                summary_lines.append(stripped)
                if len(summary_lines) >= 2:
                    break

        summary = " ".join(summary_lines) if summary_lines else None

        # Truncate summary if too long
        if summary and len(summary) > 100:
            summary = summary[:97] + "..."

        # Calculate progress from progress.md
        progress_summary = self._calculate_progress(worktree_path)

        # Return folder path, not plan.md file path
        plan_folder = worktree_path / ".plan"

        return PlanStatus(
            exists=True,
            path=plan_folder,
            summary=summary,
            line_count=line_count,
            first_lines=first_lines,
            progress_summary=progress_summary,
            format="folder",
        )

    def _calculate_progress(self, worktree_path: Path) -> str | None:
        """Calculate progress from progress.md checkboxes.

        Args:
            worktree_path: Path to worktree

        Returns:
            Progress string like "3/10 steps completed" or None if no progress file
        """
        progress_path = get_progress_path(worktree_path)
        if progress_path is None:
            return None

        content = progress_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Count checked and unchecked boxes
        checked = sum(1 for line in lines if line.strip().startswith("- [x]"))
        unchecked = sum(1 for line in lines if line.strip().startswith("- [ ]"))
        total = checked + unchecked

        if total == 0:
            return None

        return f"{checked}/{total} steps completed"
