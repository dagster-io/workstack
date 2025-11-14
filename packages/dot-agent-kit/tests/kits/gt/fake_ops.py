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

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.ops import (
    GitGtKitOps,
    GitHubGtKitOps,
    GraphiteGtKitOps,
    GtKitOps,
)


@dataclass(frozen=True)
class GitState:
    """Immutable git repository state."""

    current_branch: str = "main"
    uncommitted_files: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    branch_parents: dict[str, str] = field(default_factory=dict)
    add_success: bool = True
    trunk_branch: str = "main"


@dataclass(frozen=True)
class GraphiteState:
    """Immutable Graphite stack state."""

    branch_parents: dict[str, str] = field(default_factory=dict)
    branch_children: dict[str, list[str]] = field(default_factory=dict)
    submit_success: bool = True
    submit_stdout: str = ""
    submit_stderr: str = ""
    restack_success: bool = True
    squash_success: bool = True


@dataclass(frozen=True)
class GitHubState:
    """Immutable GitHub PR state."""

    pr_numbers: dict[str, int] = field(default_factory=dict)
    pr_urls: dict[str, str] = field(default_factory=dict)
    pr_states: dict[str, str] = field(default_factory=dict)
    pr_titles: dict[int, str] = field(default_factory=dict)
    pr_bodies: dict[int, str] = field(default_factory=dict)
    merge_success: bool = True
    pr_update_success: bool = True
    pr_delay_attempts_until_visible: int = 0


class FakeGitGtKitOps(GitGtKitOps):
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
        return self._state.add_success

    def commit(self, message: str) -> bool:
        """Create a commit and clear uncommitted files."""
        # Create new state with commit added and uncommitted files cleared
        new_commits = [*self._state.commits, message]
        self._state = replace(self._state, commits=new_commits, uncommitted_files=[])
        return True

    def amend_commit(self, message: str) -> bool:
        """Amend the current commit message."""
        if not self._state.commits:
            return False

        # Replace last commit message
        new_commits = [*self._state.commits[:-1], message]
        self._state = replace(self._state, commits=new_commits)
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


class FakeGraphiteGtKitOps(GraphiteGtKitOps):
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

    def squash_commits(self) -> bool:
        """Run gt squash with configurable success/failure."""
        return self._state.squash_success

    def submit(self, publish: bool = False, restack: bool = False) -> tuple[bool, str, str]:
        """Run gt submit with configurable success/failure."""
        return (
            self._state.submit_success,
            self._state.submit_stdout,
            self._state.submit_stderr,
        )

    def restack(self) -> bool:
        """Run gt restack with configurable success/failure."""
        return self._state.restack_success

    def navigate_to_child(self) -> bool:
        """Navigate to child branch (always succeeds in fake)."""
        children = self.get_children_branches()
        if len(children) == 1:
            self._current_branch = children[0]
            return True
        return False


class FakeGitHubGtKitOps(GitHubGtKitOps):
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

    def merge_pr(self) -> bool:
        """Merge the PR with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        return self._state.merge_success

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL (fake returns test URL)."""
        return f"https://app.graphite.dev/github/pr/test-owner/test-repo/{pr_number}"


class FakeGtKitOps(GtKitOps):
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

    def with_pr(self, number: int, url: str | None = None, state: str = "OPEN") -> "FakeGtKitOps":
        """Set PR for current branch.

        Args:
            number: PR number
            url: PR URL (auto-generated if None)
            state: PR state (default: OPEN)

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

        self._github._state = replace(
            gh_state,
            pr_numbers=new_pr_numbers,
            pr_urls=new_pr_urls,
            pr_states=new_pr_states,
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

    def with_restack_failure(self) -> "FakeGtKitOps":
        """Configure restack to fail.

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(gt_state, restack_success=False)
        return self

    def with_merge_failure(self) -> "FakeGtKitOps":
        """Configure PR merge to fail.

        Returns:
            Self for chaining
        """
        gh_state = self._github.get_state()
        self._github._state = replace(gh_state, merge_success=False)
        return self

    def with_squash_failure(self) -> "FakeGtKitOps":
        """Configure squash to fail.

        Returns:
            Self for chaining
        """
        gt_state = self._graphite.get_state()
        self._graphite._state = replace(gt_state, squash_success=False)
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
