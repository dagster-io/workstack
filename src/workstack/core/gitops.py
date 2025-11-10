"""High-level git operations interface.

This module provides a clean abstraction over git subprocess calls, making the
codebase more testable and maintainable.

Architecture:
- GitOps: Abstract base class defining the interface
- RealGitOps: Production implementation using subprocess
- Standalone functions: Convenience wrappers delegating to module singleton
"""

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class WorktreeInfo:
    """Information about a single git worktree."""

    path: Path
    branch: str | None
    is_root: bool = False


# ============================================================================
# Abstract Interface
# ============================================================================


class GitOps(ABC):
    """Abstract interface for git operations.

    All implementations (real and fake) must implement this interface.
    This interface contains ONLY runtime operations - no test setup methods.
    """

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        ...

    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        ...

    @abstractmethod
    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect the default branch (main or master).

        Args:
            repo_root: Path to the repository root
            configured: Optional configured trunk branch name. If provided, validates
                       that this branch exists. If None, uses auto-detection.

        Returns:
            The trunk branch name

        Raises:
            SystemExit: If configured branch doesn't exist or no trunk can be detected
        """
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        ...

    @abstractmethod
    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        ...

    @abstractmethod
    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes.

        Uses git status --porcelain to detect any uncommitted changes.
        Returns False if git command fails (worktree might be in invalid state).

        Args:
            cwd: Working directory to check

        Returns:
            True if there are any uncommitted changes (staged, modified, or untracked)
        """
        ...

    @abstractmethod
    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new git worktree.

        Args:
            repo_root: Path to the git repository root
            path: Path where the worktree should be created
            branch: Branch name (None creates detached HEAD or uses ref)
            ref: Git ref to base worktree on (None defaults to HEAD when creating branches)
            create_branch: True to create new branch, False to checkout existing
        """
        ...

    @abstractmethod
    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location."""
        ...

    @abstractmethod
    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree.

        Args:
            repo_root: Path to the git repository root
            path: Path to the worktree to remove
            force: True to force removal even if worktree has uncommitted changes
        """
        ...

    @abstractmethod
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref (commit SHA, branch, etc)."""
        ...

    @abstractmethod
    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        ...

    @abstractmethod
    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        ...

    @abstractmethod
    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to check

        Returns:
            Path to the worktree where branch is checked out, or None if not checked out.
        """
        ...

    @abstractmethod
    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name.

        Args:
            repo_root: Repository root path
            branch: Branch name to search for

        Returns:
            Path to worktree if branch is checked out, None otherwise
        """
        ...

    @abstractmethod
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to query

        Returns:
            Commit SHA as a string, or None if branch doesn't exist.
        """
        ...

    @abstractmethod
    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the commit message for a given commit SHA.

        Args:
            repo_root: Path to the git repository root
            commit_sha: Commit SHA to query

        Returns:
            First line of commit message, or None if commit doesn't exist.
        """
        ...

    @abstractmethod
    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files.

        Args:
            cwd: Working directory

        Returns:
            Tuple of (staged, modified, untracked) file lists
        """
        ...

    @abstractmethod
    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch.

        Args:
            cwd: Working directory
            branch: Current branch name

        Returns:
            Tuple of (ahead, behind) counts
        """
        ...

    @abstractmethod
    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information.

        Args:
            cwd: Working directory
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit info dicts with keys: sha, message, author, date
        """
        ...


# ============================================================================
# Production Implementation
# ============================================================================


class RealGitOps(GitOps):
    """Production implementation using subprocess.

    All git operations execute actual git commands via subprocess.
    """

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        worktrees: list[WorktreeInfo] = []
        current_path: Path | None = None
        current_branch: str | None = None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("worktree "):
                current_path = Path(line.split(maxsplit=1)[1])
                current_branch = None
            elif line.startswith("branch "):
                if current_path is None:
                    continue
                branch_ref = line.split(maxsplit=1)[1]
                current_branch = branch_ref.replace("refs/heads/", "")
            elif line == "" and current_path is not None:
                worktrees.append(WorktreeInfo(path=current_path, branch=current_branch))
                current_path = None
                current_branch = None

        if current_path is not None:
            worktrees.append(WorktreeInfo(path=current_path, branch=current_branch))

        # Mark first worktree as root (git guarantees this ordering)
        if worktrees:
            first = worktrees[0]
            worktrees[0] = WorktreeInfo(path=first.path, branch=first.branch, is_root=True)

        return worktrees

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        branch = result.stdout.strip()
        if branch == "HEAD":
            return None

        return branch

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect the default branch (main or master)."""
        # If trunk is explicitly configured, validate and use it
        if configured is not None:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", configured],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return configured
            click.echo(
                f"Error: Configured trunk branch '{configured}' does not exist in repository.\n"
                f"Update your configuration in pyproject.toml or create the branch.",
                err=True,
            )
            raise SystemExit(1)

        # Auto-detection: try remote HEAD first
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            remote_head = result.stdout.strip()
            if remote_head.startswith("refs/remotes/origin/"):
                branch = remote_head.replace("refs/remotes/origin/", "")
                return branch

        # Fallback: check master first, then main
        for candidate in ["master", "main"]:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        click.echo("Error: Could not find 'main' or 'master' branch.", err=True)
        raise SystemExit(1)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        git_dir = Path(result.stdout.strip())
        if not git_dir.is_absolute():
            git_dir = cwd / git_dir

        return git_dir.resolve()

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in (0, 1):
            return result.returncode == 1
        result.check_returncode()
        return False

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new git worktree."""
        if branch and not create_branch:
            cmd = ["git", "worktree", "add", str(path), branch]
        elif branch and create_branch:
            base_ref = ref or "HEAD"
            cmd = ["git", "worktree", "add", "-b", branch, str(path), base_ref]
        else:
            base_ref = ref or "HEAD"
            cmd = ["git", "worktree", "add", str(path), base_ref]

        subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True, text=True)

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location."""
        cmd = ["git", "worktree", "move", str(old_path), str(new_path)]
        subprocess.run(cmd, cwd=repo_root, check=True)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree."""
        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(str(path))
        subprocess.run(cmd, cwd=repo_root, check=True)

        # Clean up git worktree metadata to prevent permission issues during test cleanup
        # This prunes stale administrative files left behind after worktree removal
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        subprocess.run(
            ["git", "checkout", branch],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        subprocess.run(
            ["git", "checkout", "--detach", ref],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        cmd = ["gt", "delete", branch]
        if force:
            cmd.insert(2, "-f")
        subprocess.run(cmd, cwd=repo_root, check=True)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root, check=True)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        result = subprocess.run(
            ["git", "rev-parse", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the first line of commit message for a given commit SHA."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s", commit_sha],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        staged = []
        modified = []
        untracked = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            # Check if file is staged (first character is not space)
            if status_code[0] != " " and status_code[0] != "?":
                staged.append(filename)

            # Check if file is modified (second character is not space)
            if status_code[1] != " " and status_code[1] != "?":
                modified.append(filename)

            # Check if file is untracked
            if status_code == "??":
                untracked.append(filename)

        return staged, modified, untracked

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        # Check if branch has upstream
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # No upstream branch
            return 0, 0

        upstream = result.stdout.strip()

        # Get ahead/behind counts
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        parts = result.stdout.strip().split()
        if len(parts) == 2:
            behind = int(parts[0])
            ahead = int(parts[1])
            return ahead, behind

        return 0, 0

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information."""
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{limit}",
                "--format=%H%x00%s%x00%an%x00%ar",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append(
                    {
                        "sha": parts[0][:7],  # Short SHA
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    }
                )

        return commits


# ============================================================================
# Dry-Run Wrapper
# ============================================================================


class DryRunGitOps(GitOps):
    """Wrapper that prints dry-run messages instead of executing destructive operations.

    This wrapper intercepts destructive git operations and prints what would happen
    instead of executing. Read-only operations are delegated to the wrapped implementation.

    Usage:
        real_ops = RealGitOps()
        dry_run_ops = DryRunGitOps(real_ops)

        # Prints message instead of deleting
        dry_run_ops.remove_worktree(repo_root, path, force=False)
    """

    def __init__(self, wrapped: GitOps) -> None:
        """Create a dry-run wrapper around a GitOps implementation.

        Args:
            wrapped: The GitOps implementation to wrap (usually RealGitOps or FakeGitOps)
        """
        self._wrapped = wrapped

    # Read-only operations: delegate to wrapped implementation

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees (read-only, delegates to wrapped)."""
        return self._wrapped.list_worktrees(repo_root)

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get current branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_current_branch(cwd)

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect default branch (read-only, delegates to wrapped)."""
        return self._wrapped.detect_default_branch(repo_root, configured)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout branch (delegates to wrapped - considered read-only for dry-run)."""
        return self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout detached HEAD (delegates to wrapped - considered read-only for dry-run)."""
        return self._wrapped.checkout_detached(cwd, ref)

    # Destructive operations: print dry-run message instead of executing

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Print dry-run message instead of adding worktree."""
        if branch and create_branch:
            base_ref = ref or "HEAD"
            click.echo(
                f"[DRY RUN] Would run: git worktree add -b {branch} {path} {base_ref}",
                err=True,
            )
        elif branch:
            click.echo(f"[DRY RUN] Would run: git worktree add {path} {branch}", err=True)
        else:
            base_ref = ref or "HEAD"
            click.echo(f"[DRY RUN] Would run: git worktree add {path} {base_ref}", err=True)

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Print dry-run message instead of moving worktree."""
        click.echo(f"[DRY RUN] Would run: git worktree move {old_path} {new_path}", err=True)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Print dry-run message instead of removing worktree."""
        force_flag = "--force " if force else ""
        click.echo(f"[DRY RUN] Would run: git worktree remove {force_flag}{path}", err=True)

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Print dry-run message instead of deleting branch."""
        force_flag = "-f " if force else ""
        click.echo(f"[DRY RUN] Would run: gt delete {force_flag}{branch}", err=True)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Print dry-run message instead of pruning worktrees."""
        click.echo("[DRY RUN] Would run: git worktree prune", err=True)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if branch is checked out (read-only, delegates to wrapped)."""
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for branch (read-only, delegates to wrapped)."""
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get branch head commit SHA (read-only, delegates to wrapped)."""
        return self._wrapped.get_branch_head(repo_root, branch)

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, delegates to wrapped)."""
        return self._wrapped.get_file_status(cwd)

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get ahead/behind counts (read-only, delegates to wrapped)."""
        return self._wrapped.get_ahead_behind(cwd, branch)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, delegates to wrapped)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)
