"""Plan file collector."""

from pathlib import Path

import frontmatter

from erk.core.context import ErkContext
from erk.core.plan_folder import (
    get_plan_path,
    get_progress_path,
    parse_progress_frontmatter,
    update_progress_frontmatter,
)
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import PlanStatus


def detect_enriched_plan(repo_root: Path) -> tuple[Path | None, str | None]:
    """Detect enriched plan file at repository root.

    Scans for *-plan.md files and checks for erk_plan marker.

    Args:
        repo_root: Repository root path

    Returns:
        Tuple of (path, filename) or (None, None) if not found
    """
    if not repo_root.exists():
        return None, None

    # Find all *-plan.md files
    plan_files = list(repo_root.glob("*-plan.md"))

    if not plan_files:
        return None, None

    # Sort by modification time (most recent first)
    plan_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Check each file for enrichment marker
    for plan_file in plan_files:
        # Use frontmatter library to parse YAML frontmatter
        post = frontmatter.load(str(plan_file))

        # Check for enrichment marker (handles missing frontmatter gracefully)
        if post.get("erk_plan") is True:
            return plan_file, plan_file.name

    return None, None


class PlanFileCollector(StatusCollector):
    """Collects information about .plan/ folder."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "plan"

    def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
        """Check if .plan/plan.md exists.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree

        Returns:
            True if .plan/plan.md exists
        """
        plan_path = get_plan_path(worktree_path, git_ops=ctx.git)
        return plan_path is not None

    def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> PlanStatus | None:
        """Collect plan folder information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            PlanStatus with folder information or None if collection fails
        """
        plan_path = get_plan_path(worktree_path, git_ops=ctx.git)

        # Detect enriched plan at repo root
        enriched_plan_path, enriched_plan_filename = detect_enriched_plan(repo_root)

        if plan_path is None:
            return PlanStatus(
                exists=False,
                path=None,
                summary=None,
                line_count=0,
                first_lines=[],
                progress_summary=None,
                format="none",
                enriched_plan_path=enriched_plan_path,
                enriched_plan_filename=enriched_plan_filename,
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
        progress_summary, completion_percentage = self._calculate_progress(worktree_path)

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
            completion_percentage=completion_percentage,
            enriched_plan_path=enriched_plan_path,
            enriched_plan_filename=enriched_plan_filename,
        )

    def _calculate_progress(self, worktree_path: Path) -> tuple[str | None, int | None]:
        """Calculate progress from progress.md checkboxes and front matter.

        Args:
            worktree_path: Path to worktree

        Returns:
            Tuple of (progress_summary, completion_percentage)
            - progress_summary: String like "3/10 steps completed" or None
            - completion_percentage: Integer 0-100 or None if no front matter
        """
        progress_path = get_progress_path(worktree_path)
        if progress_path is None:
            return None, None

        content = progress_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Count checked and unchecked boxes (source of truth)
        checked = sum(1 for line in lines if line.strip().startswith("- [x]"))
        unchecked = sum(1 for line in lines if line.strip().startswith("- [ ]"))
        total = checked + unchecked

        if total == 0:
            return None, None

        # Parse front matter
        front_matter = parse_progress_frontmatter(content)

        # Calculate completion percentage only if front matter exists
        completion_percentage = None
        if front_matter is not None:
            # Auto-sync if counts differ from front matter
            fm_completed = front_matter.get("completed_steps", 0)
            fm_total = front_matter.get("total_steps", 0)

            if fm_completed != checked or fm_total != total:
                # Update front matter to match checkbox reality
                update_progress_frontmatter(worktree_path, checked, total)

            # Calculate percentage (checkboxes are source of truth)
            completion_percentage = int((checked / total) * 100)

        progress_summary = f"{checked}/{total} steps completed"
        return progress_summary, completion_percentage
