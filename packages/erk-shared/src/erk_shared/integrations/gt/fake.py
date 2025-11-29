"""In-memory fake implementations of GT kit operations for testing.

This module provides fake implementations with declarative setup methods that
eliminate the need for extensive subprocess mocking in tests.

Design:
- Immutable state using frozen dataclasses
- Declarative setup methods (with_branch, with_uncommitted_files, etc.)
- Automatic state transitions (commit clears uncommitted files)
- LBYL pattern: methods check state before operations
- Returns match interface contracts exactly
"""

from dataclasses import dataclass, field, replace

from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit, GraphiteGtKit, GtKit
from erk_shared.integrations.gt.types import CommandResult


@dataclass(frozen=True)
class GitState:
    """Immutable git repository state."""

    current_branch: str = "main"
    uncommitted_files: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    branch_parents: dict[str, str] = field(default_factory=dict)
    add_success: bool = True
    trunk_branch: str = "main"
    tracked_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GraphiteState:
    """Immutable Graphite stack state."""

    branch_parents: dict[str, str] = field(default_factory=dict)
    branch_children: dict[str, list[str]] = field(default_factory=dict)
    submit_success: bool = True
    submit_stdout: str = ""
    submit_stderr: str = ""
    restack_success: bool = True
    restack_stdout: str = ""
    restack_stderr: str = ""
    squash_success: bool = True
    squash_stdout: str = ""
    squash_stderr: str = ""
    authenticated: bool = True
    auth_username: str | None = "test-user"
    auth_repo_info: str | None = "owner/repo"


@dataclass(frozen=True)
class GitHubState:
    """Immutable GitHub PR state."""

    pr_numbers: dict[str, int] = field(default_factory=dict)
    pr_urls: dict[str, str] = field(default_factory=dict)
    pr_states: dict[str, str] = field(default_factory=dict)
    pr_titles: dict[int, str] = field(default_factory=dict)
    pr_bodies: dict[int, str] = field(default_factory=dict)
    pr_diffs: dict[int, str] = field(default_factory=dict)
    pr_mergeability: dict[int, tuple[str, str]] = field(default_factory=dict)
    merge_success: bool = True
    pr_update_success: bool = True
    pr_delay_attempts_until_visible: int = 0
    authenticated: bool = True
    auth_username: str | None = "test-user"
    auth_hostname: str | None = "github.com"


class FakeGitGtKitOps(GitGtKit):
    """Fake git operations with in-memory state."""

    def __init__(self, state: GitState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitState()

    def get_state(self) -> GitState:
        """Get current state (for testing assertions)."""
        return self._state

    def get_current_branch(self) -> str | None:
        """Get the name of the current branch."""
        if not self._state.current_branch:
            return None
        return self._state.current_branch

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        return len(self._state.uncommitted_files) > 0

    def add_all(self) -> bool:
        """Stage all changes with configurable success/failure."""
        if not self._state.add_success:
            return False

        # Track staged files separately for proper simulation
        # In a real git workflow, add_all stages files but doesn't commit them
        # For our fake, we'll track this via a staged_files field
        if not hasattr(self, "_staged_files"):
            self._staged_files: list[str] = []
        self._staged_files = list(self._state.uncommitted_files)
        return True

    def commit(self, message: str) -> bool:
        """Create a commit and clear uncommitted files."""
        # Create new state with commit added and uncommitted files cleared
        new_commits = [*self._state.commits, message]
        # Track committed files in the state
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after commit
        if hasattr(self, "_staged_files"):
            self._staged_files = []
        return True

    def amend_commit(self, message: str) -> bool:
        """Amend the current commit message and include any staged changes."""
        if not self._state.commits:
            return False

        # Replace last commit message
        new_commits = [*self._state.commits[:-1], message]
        # Amend should include staged files and clear uncommitted files
        # (since they're now part of the amended commit)
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after amend
        if hasattr(self, "_staged_files"):
            self._staged_files = []
        return True

    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch.

        For fakes, this returns the total number of commits since we don't
        track per-branch commit history in detail.
        """
        return len(self._state.commits)

    def get_trunk_branch(self) -> str:
        """Get the trunk branch name for the repository."""
        return self._state.trunk_branch

    def get_repository_root(self) -> str:
        """Fake repository root."""
        return "/fake/repo/root"

    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Fake diff output."""
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def check_merge_conflicts(self, base_branch: str, head_branch: str) -> bool:
        """Fake conflict checker - returns False unless configured otherwise."""
        # Check if fake has been configured to simulate conflicts
        if hasattr(self, "_simulated_conflicts"):
            return (base_branch, head_branch) in self._simulated_conflicts
        return False

    def simulate_conflict(self, base_branch: str, head_branch: str) -> None:
        """Configure fake to simulate conflicts for specific branch pair."""
        if not hasattr(self, "_simulated_conflicts"):
            self._simulated_conflicts: set[tuple[str, str]] = set()
        self._simulated_conflicts.add((base_branch, head_branch))


class FakeGraphiteGtKitOps(GraphiteGtKit):
    """Fake Graphite operations with in-memory state."""

    def __init__(self, state: GraphiteState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GraphiteState()
        self._current_branch = "main"

    def set_current_branch(self, branch: str) -> None:
        """Set current branch (needed for context)."""
        self._current_branch = branch

    def get_state(self) -> GraphiteState:
        """Get current state (for testing assertions)."""
        return self._state

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status."""
        if not self._state.authenticated:
            return (False, None, None)
        return (True, self._state.auth_username, self._state.auth_repo_info)

    def get_parent_branch(self) -> str | None:
        """Get the parent branch for current branch."""
        if self._current_branch not in self._state.branch_parents:
            return None
        return self._state.branch_parents[self._current_branch]

    def get_children_branches(self) -> list[str]:
        """Get list of child branches for current branch."""
        if self._current_branch not in self._state.branch_children:
            return []
        return self._state.branch_children[self._current_branch]

    def squash_commits(self) -> CommandResult:
        """Run gt squash with configurable success/failure."""
        return CommandResult(
            success=self._state.squash_success,
            stdout=self._state.squash_stdout,
            stderr=self._state.squash_stderr,
        )

    def submit(self, publish: bool = False, restack: bool = False) -> CommandResult:
        """Run gt submit with configurable success/failure."""
        return CommandResult(
            success=self._state.submit_success,
            stdout=self._state.submit_stdout,
            stderr=self._state.submit_stderr,
        )

    def restack(self) -> CommandResult:
        """Run gt restack with configurable success/failure."""
        return CommandResult(
            success=self._state.restack_success,
            stdout=self._state.restack_stdout,
            stderr=self._state.restack_stderr,
        )

    def navigate_to_child(self) -> bool:
        """Navigate to child branch (always succeeds in fake)."""
        children = self.get_children_branches()
        if len(children) == 1:
            self._current_branch = children[0]
            return True
        return False


class FakeGitHubGtKitOps(GitHubGtKit):
    """Fake GitHub operations with in-memory state."""

    def __init__(self, state: GitHubState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitHubState()
        self._current_branch = "main"
        self._pr_info_attempt_count = 0

    def set_current_branch(self, branch: str) -> None:
        """Set current branch (needed for context)."""
        self._current_branch = branch

    def get_state(self) -> GitHubState:
        """Get current state (for testing assertions)."""
        return self._state

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status."""
        if not self._state.authenticated:
            return (False, None, None)
        return (True, self._state.auth_username, self._state.auth_hostname)

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch."""
        # Simulate PR delay if configured
        if self._state.pr_delay_attempts_until_visible > 0:
            self._pr_info_attempt_count += 1
            if self._pr_info_attempt_count <= self._state.pr_delay_attempts_until_visible:
                return None

        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_url = self._state.pr_urls.get(
            self._current_branch, f"https://github.com/repo/pull/{pr_number}"
        )
        return (pr_number, pr_url)

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_state = self._state.pr_states.get(self._current_branch, "OPEN")
        return (pr_number, pr_state)

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False

        if not self._state.pr_update_success:
            return False

        pr_number = self._state.pr_numbers[self._current_branch]

        # Create new state with updated metadata
        new_titles = {**self._state.pr_titles, pr_number: title}
        new_bodies = {**self._state.pr_bodies, pr_number: body}
        self._state = replace(self._state, pr_titles=new_titles, pr_bodies=new_bodies)
        return True

    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review (fake always succeeds if PR exists)."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        # In the fake, marking as ready always succeeds if PR exists
        return True

    def get_pr_title(self) -> str | None:
        """Get the title of the PR for the current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None
        pr_number = self._state.pr_numbers[self._current_branch]
        return self._state.pr_titles.get(pr_number)

    def merge_pr(self, *, subject: str | None = None) -> bool:
        """Merge the PR with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        return self._state.merge_success

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL (fake returns test URL)."""
        return f"https://app.graphite.com/github/pr/test-owner/test-repo/{pr_number}"

    def get_pr_diff(self, pr_number: int) -> str:
        """Get PR diff from configured state or return default."""
        if pr_number in self._state.pr_diffs:
            return self._state.pr_diffs[pr_number]
        # Return a simple default diff
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for branch from fake state."""
        if branch not in self._state.pr_numbers:
            return (None, None)

        pr_number = self._state.pr_numbers[branch]
        pr_url = self._state.pr_urls.get(branch, f"https://github.com/repo/pull/{pr_number}")
        return (pr_number, pr_url)

    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from fake state."""
        # Default: MERGEABLE/CLEAN unless configured otherwise
        return self._state.pr_mergeability.get(pr_number, ("MERGEABLE", "CLEAN"))


class FakeGtKitOps(GtKit):
    """Fake composite operations for testing.

    Provides declarative setup methods for common test scenarios.
    """

    def __init__(
        self,
        git_state: GitState | None = None,
        graphite_state: GraphiteState | None = None,
        github_state: GitHubState | None = None,
    ) -> None:
        """Initialize with optional initial states."""
        self._git = FakeGitGtKitOps(git_state)
        self._graphite = FakeGraphiteGtKitOps(graphite_state)
        self._github = FakeGitHubGtKitOps(github_state)

    def git(self) -> FakeGitGtKitOps:
        """Get the git operations interface."""
        return self._git

    def graphite(self) -> FakeGraphiteGtKitOps:
        """Get the Graphite operations interface."""
        return self._graphite

    def github(self) -> FakeGitHubGtKitOps:
        """Get the GitHub operations interface."""
        return self._github

    # Declarative setup methods

    def with_branch(self, branch: str, parent: str = "main") -> "FakeGtKitOps":
        """Set current branch and its parent.

        Args:
            branch: Branch name
            parent: Parent branch name

        Returns:
            Self for chaining
        """
        # Update git state
        git_state = self._git.get_state()
        self._git._state = replace(git_state, current_branch=branch)

        # Update graphite state with parent relationship
        gt_state = self._graphite.get_state()
        new_parents = {**gt_state.branch_parents, branch: parent}
        self._graphite._state = replace(gt_state, branch_parents=new_parents)
        self._graphite.set_current_branch(branch)

        # Update github state
        self._github.set_current_branch(branch)

        return self

    def with_uncommitted_files(self, files: list[str]) -> "FakeGtKitOps":
        """Set uncommitted files.

        Args:
            files: List of file paths

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, uncommitted_files=files)
        return self

    def with_commits(self, count: int) -> "FakeGtKitOps":
        """Add a number of commits.

        Args:
            count: Number of commits to add

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        commits = [f"commit-{i}" for i in range(count)]
        self._git._state = replace(git_state, commits=commits)
        return self

    def with_pr(
        self, number: int, url: str | None = None, state: str = "OPEN", title: str | None = None
    ) -> "FakeGtKitOps":
        """Set PR for current branch.

        Args:
            number: PR number
            url: PR URL (auto-generated if None)
            state: PR state (default: OPEN)
            title: PR title (optional)

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        branch = self._github._current_branch

        if url is None:
            url = f"https://github.com/repo/pull/{number}"

        new_pr_numbers = {**gh_state.pr_numbers, branch: number}
        new_pr_urls = {**gh_state.pr_urls, branch: url}
        new_pr_states = {**gh_state.pr_states, branch: state}
        new_pr_titles = gh_state.pr_titles
        if title is not None:
            new_pr_titles = {**gh_state.pr_titles, number: title}

        self._github._state = replace(
            gh_state,
            pr_numbers=new_pr_numbers,
            pr_urls=new_pr_urls,
            pr_states=new_pr_states,
            pr_titles=new_pr_titles,
        )
        return self

    def with_children(self, children: list[str]) -> "FakeGtKitOps":
        """Set child branches for current branch.

        Args:
            children: List of child branch names

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        branch = self._graphite._current_branch

        new_children = {**gt_state.branch_children, branch: children}
        self._graphite._state = replace(gt_state, branch_children=new_children)
        return self

    def with_submit_failure(self, stdout: str = "", stderr: str = "") -> "FakeGtKitOps":
        """Configure submit to fail.

        Args:
            stdout: Stdout to return
            stderr: Stderr to return

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(
            gt_state, submit_success=False, submit_stdout=stdout, submit_stderr=stderr
        )
        return self

    def with_restack_failure(self, stdout: str = "", stderr: str = "") -> "FakeGtKitOps":
        """Configure restack to fail.

        Args:
            stdout: Stdout to return
            stderr: Stderr to return

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(
            gt_state, restack_success=False, restack_stdout=stdout, restack_stderr=stderr
        )
        return self

    def with_merge_failure(self) -> "FakeGtKitOps":
        """Configure PR merge to fail.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(gh_state, merge_success=False)
        return self

    def with_squash_failure(self, stdout: str = "", stderr: str = "") -> "FakeGtKitOps":
        """Configure squash to fail.

        Args:
            stdout: Stdout to return
            stderr: Stderr to return

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(
            gt_state, squash_success=False, squash_stdout=stdout, squash_stderr=stderr
        )
        return self

    def with_add_failure(self) -> "FakeGtKitOps":
        """Configure git add to fail.

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, add_success=False)
        return self

    def with_pr_update_failure(self) -> "FakeGtKitOps":
        """Configure PR metadata update to fail.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(gh_state, pr_update_success=False)
        return self

    def with_pr_delay(self, attempts_until_visible: int) -> "FakeGtKitOps":
        """Configure PR to appear only after N get_pr_info() attempts.

        Simulates GitHub API delay where PR is not immediately visible after creation.

        Args:
            attempts_until_visible: Number of attempts that return None before PR appears

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(
            gh_state, pr_delay_attempts_until_visible=attempts_until_visible
        )
        return self

    def with_submit_success_but_nothing_submitted(self) -> "FakeGtKitOps":
        """Configure submit to succeed but with 'Nothing to submit!' warning.

        Simulates the case where a parent branch is empty/already merged.
        Graphite returns exit code 0 but with warning text.

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(
            gt_state,
            submit_success=True,
            submit_stdout=(
                "WARNING: This branch does not introduce any changes:\n"
                "▸ stale-parent-branch\n"
                "WARNING: This branch and any dependent branches will not be submitted.\n"
                "Nothing to submit!"
            ),
            submit_stderr="",
        )
        return self

    def with_gt_unauthenticated(self) -> "FakeGtKitOps":
        """Configure Graphite as not authenticated.

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(
            gt_state,
            authenticated=False,
            auth_username=None,
            auth_repo_info=None,
        )
        return self

    def with_gh_unauthenticated(self) -> "FakeGtKitOps":
        """Configure GitHub as not authenticated.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(
            gh_state,
            authenticated=False,
            auth_username=None,
            auth_hostname=None,
        )
        return self

    def with_pr_conflicts(self, pr_number: int) -> "FakeGtKitOps":
        """Configure PR to have merge conflicts.

        Args:
            pr_number: PR number to configure as conflicting

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        new_mergeability = {
            **gh_state.pr_mergeability,
            pr_number: ("CONFLICTING", "DIRTY"),
        }
        self._github._state = replace(gh_state, pr_mergeability=new_mergeability)
        return self

    def with_pr_mergeability(
        self, pr_number: int, mergeable: str, merge_state: str
    ) -> "FakeGtKitOps":
        """Configure PR mergeability status.

        Args:
            pr_number: PR number to configure
            mergeable: Mergeability status ("MERGEABLE", "CONFLICTING", "UNKNOWN")
            merge_state: Merge state status ("CLEAN", "DIRTY", "UNSTABLE", etc.)

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        new_mergeability = {
            **gh_state.pr_mergeability,
            pr_number: (mergeable, merge_state),
        }
        self._github._state = replace(gh_state, pr_mergeability=new_mergeability)
        return self
