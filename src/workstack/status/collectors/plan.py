"""Plan file collector."""

from pathlib import Path

from workstack.core.context import WorkstackContext
from workstack.status.collectors.base import StatusCollector
from workstack.status.models.status_data import PlanStatus


class PlanFileCollector(StatusCollector):
    """Collects information about .PLAN.md file."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "plan"

    def is_available(self, ctx: WorkstackContext, worktree_path: Path) -> bool:
        """Check if .PLAN.md exists.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree

        Returns:
            True if .PLAN.md exists
        """
        plan_path = worktree_path / ".PLAN.md"
        return ctx.git_ops.path_exists(plan_path)

    def collect(
        self, ctx: WorkstackContext, worktree_path: Path, repo_root: Path
    ) -> PlanStatus | None:
        """Collect plan file information.

        Args:
            ctx: Workstack context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PlanStatus with file information or None if collection fails
        """
        plan_path = worktree_path / ".PLAN.md"

        if not ctx.git_ops.path_exists(plan_path):
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
            )

        # Read the file
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

        return PlanStatus(
            exists=True,
            path=plan_path,
            summary=summary,
            line_count=line_count,
            first_lines=first_lines,
        )
