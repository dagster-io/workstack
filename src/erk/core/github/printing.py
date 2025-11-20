"""Printing wrapper for GitHub operations."""

from pathlib import Path

from erk.core.github.abc import GitHub
from erk.core.github.types import PRInfo, PRMergeability, PullRequestInfo
from erk.core.printing_base import PrintingBase


class PrintingGitHub(PrintingBase, GitHub):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_ops = PrintingGitHub(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = NoopGitHub(real_ops)
        printing_ops = PrintingGitHub(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # Read-only operations: delegate without printing

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PRs (read-only, no printing)."""
        return self._wrapped.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status (read-only, no printing)."""
        return self._wrapped.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR base branch (read-only, no printing)."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability (read-only, no printing)."""
        return self._wrapped.get_pr_mergeability(repo_root, pr_number)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PRs with CI status and mergeability (read-only, no printing)."""
        return self._wrapped.enrich_prs_with_ci_status_batch(prs, repo_root)

    # Operations that need printing

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update PR base branch with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --base {new_base}"))
        self._wrapped.update_pr_base_branch(repo_root, pr_number, new_base)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge PR with printed output."""
        merge_type = "--squash" if squash else "--merge"
        self._emit(self._format_command(f"gh pr merge {pr_number} {merge_type}"))
        self._wrapped.merge_pr(repo_root, pr_number, squash=squash, verbose=verbose)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
    ) -> None:
        """Trigger workflow with printed output."""
        input_args = " ".join(f"-f {key}={value}" for key, value in inputs.items())
        self._emit(self._format_command(f"gh workflow run {workflow} {input_args}"))
        self._wrapped.trigger_workflow(repo_root, workflow, inputs)
