"""Fake GitHub operations for testing.

FakeGitHub is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path
from typing import cast

from erk_shared.github.abc import GitHub
from erk_shared.github.types import PRInfo, PRMergeability, PRState, PullRequestInfo, WorkflowRun


class FakeGitHub(GitHub):
    """In-memory fake implementation of GitHub operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).
    """

    def __init__(
        self,
        *,
        prs: dict[str, PullRequestInfo] | None = None,
        pr_statuses: dict[str, tuple[str | None, int | None, str | None]] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_mergeability: dict[int, PRMergeability | None] | None = None,
        workflow_runs: list[WorkflowRun] | None = None,
        run_logs: dict[str, str] | None = None,
    ) -> None:
        """Create FakeGitHub with pre-configured state.

        Args:
            prs: Mapping of branch name -> PullRequestInfo
            pr_statuses: Legacy parameter for backward compatibility.
                        Mapping of branch name -> (state, pr_number, title)
            pr_bases: Mapping of pr_number -> base_branch
            pr_mergeability: Mapping of pr_number -> PRMergeability (None for API errors)
            workflow_runs: List of WorkflowRun objects to return from list_workflow_runs
            run_logs: Mapping of run_id -> log string
        """
        if prs is not None and pr_statuses is not None:
            msg = "Cannot specify both prs and pr_statuses"
            raise ValueError(msg)

        if pr_statuses is not None:
            # Convert legacy pr_statuses format to PullRequestInfo
            self._prs = {}
            for branch, (state, pr_number, title) in pr_statuses.items():
                if pr_number is not None:
                    # Handle None state - default to "OPEN"
                    resolved_state = state if state is not None and state != "NONE" else "OPEN"
                    self._prs[branch] = PullRequestInfo(
                        number=pr_number,
                        state=resolved_state,
                        url=f"https://github.com/owner/repo/pull/{pr_number}",
                        is_draft=False,
                        title=title,
                        checks_passing=None,
                        owner="owner",
                        repo="repo",
                        has_conflicts=None,
                    )
            self._pr_statuses = pr_statuses
        else:
            self._prs = prs or {}
            self._pr_statuses = None

        self._pr_bases = pr_bases or {}
        self._pr_mergeability = pr_mergeability or {}
        self._workflow_runs = workflow_runs or []
        self._run_logs = run_logs or {}
        self._updated_pr_bases: list[tuple[int, str]] = []
        self._merged_prs: list[int] = []
        self._get_prs_for_repo_calls: list[tuple[Path, bool]] = []
        self._get_pr_status_calls: list[tuple[Path, str]] = []
        self._triggered_workflows: list[tuple[str, dict[str, str]]] = []

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._merged_prs

    @property
    def get_prs_for_repo_calls(self) -> list[tuple[Path, bool]]:
        """Read-only access to tracked get_prs_for_repo() calls for test assertions.

        Returns list of (repo_root, include_checks) tuples.
        """
        return self._get_prs_for_repo_calls

    @property
    def get_pr_status_calls(self) -> list[tuple[Path, str]]:
        """Read-only access to tracked get_pr_status() calls for test assertions.

        Returns list of (repo_root, branch) tuples.
        """
        return self._get_pr_status_calls

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches (returns pre-configured data).

        The include_checks parameter is accepted but ignored - fake returns the
        same pre-configured data regardless of this parameter.
        """
        self._get_prs_for_repo_calls.append((repo_root, include_checks))
        return self._prs

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status from configured PRs.

        Returns PRInfo("NONE", None, None) if branch not found.
        """
        # Support legacy pr_statuses format
        if self._pr_statuses is not None:
            result = self._pr_statuses.get(branch)
            if result is None:
                return PRInfo("NONE", None, None)
            state, pr_number, title = result
            # Convert None state to "NONE" for consistency
            if state is None:
                state = "NONE"
            return PRInfo(cast(PRState, state), pr_number, title)

        pr = self._prs.get(branch)
        if pr is None:
            return PRInfo("NONE", None, None)
        # PullRequestInfo has: number, state, url, is_draft, title, checks_passing
        # Return state, number, and title as expected by PRInfo
        return PRInfo(cast(PRState, pr.state), pr.number, pr.title)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from configured state.

        Returns None if PR number not found.
        """
        return self._pr_bases.get(pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Record PR base branch update in mutation tracking list."""
        self._updated_pr_bases.append((pr_number, new_base))

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from configured state.

        Returns configured mergeability or defaults to MERGEABLE if not configured.
        """
        if pr_number in self._pr_mergeability:
            return self._pr_mergeability[pr_number]
        # Default to MERGEABLE if not configured
        return PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN")

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched query.

        Fake just returns the PRs as-is. We assume PRs already have titles
        if configured. This method is a no-op that returns the input unchanged.
        """
        return prs

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PRs with CI status and mergeability using batched query.

        Fake just returns the PRs as-is. We assume PRs already have CI status
        and mergeability if configured. This method is a no-op that returns
        the input unchanged.
        """
        return prs

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Record PR merge in mutation tracking list."""
        self._merged_prs.append(pr_number)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Record workflow trigger in mutation tracking list.

        Returns:
            A fake run ID for testing
        """
        self._triggered_workflows.append((workflow, inputs))
        return "1234567890"

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
    ) -> int:
        """Record PR creation in mutation tracking list.

        Returns:
            A fake PR number for testing
        """
        # Return a fake PR number
        return 999

    @property
    def updated_pr_bases(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR base updates for test assertions."""
        return self._updated_pr_bases

    @property
    def triggered_workflows(self) -> list[tuple[str, dict[str, str]]]:
        """Read-only access to tracked workflow triggers for test assertions."""
        return self._triggered_workflows

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow (returns pre-configured data).

        Returns the pre-configured list of workflow runs. The workflow and limit
        parameters are accepted but ignored - fake returns all pre-configured runs.
        """
        return self._workflow_runs

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Return pre-configured log string for run_id.

        Raises RuntimeError if run_id not found, mimicking gh CLI behavior.
        """
        if run_id not in self._run_logs:
            msg = f"Run {run_id} not found"
            raise RuntimeError(msg)
        return self._run_logs[run_id]
