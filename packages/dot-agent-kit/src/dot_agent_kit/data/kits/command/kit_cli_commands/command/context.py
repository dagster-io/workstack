"""Context gathering for command execution."""

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitStatus:
    """Git repository status."""

    branch: str
    uncommitted_files: list[str]
    recent_commits: list[str]
    is_dirty: bool


def is_git_repo(cwd: Path) -> bool:
    """Check if directory is in a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_git_status(cwd: Path) -> GitStatus:
    """Get git repository status using subprocess."""
    # Get current branch
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Get uncommitted files
    status_output = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    uncommitted = [line.strip() for line in status_output.splitlines() if line.strip()]

    # Get recent commits
    log_output = subprocess.run(
        ["git", "log", "--oneline", "-5"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    commits = [line.strip() for line in log_output.splitlines() if line.strip()]

    return GitStatus(
        branch=branch,
        uncommitted_files=uncommitted,
        recent_commits=commits,
        is_dirty=len(uncommitted) > 0,
    )


def get_file_tree(cwd: Path, max_depth: int = 2) -> str:
    """Generate file tree structure (simplified version)."""
    # Use tree command if available, otherwise custom implementation
    try:
        result = subprocess.run(
            [
                "tree",
                "-L",
                str(max_depth),
                "-a",
                "-I",
                ".git|__pycache__|node_modules|.venv|venv",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        pass

    # Fallback: Simple directory listing
    lines = []
    for item in sorted(cwd.iterdir()):
        if item.name.startswith(".") and item.name not in [".claude", ".github"]:
            continue
        lines.append(f"  {item.name}{'/' if item.is_dir() else ''}")
    return "\n".join(lines)


def gather_context(cwd: Path) -> str:
    """Gather project context and format as markdown."""
    sections = []

    # Working directory
    sections.append(f"**Working Directory:** `{cwd}`\n")

    # Git context (if available)
    if is_git_repo(cwd):
        git_status = get_git_status(cwd)
        sections.append("**Git Status:**")
        sections.append(f"- Branch: `{git_status.branch}`")
        sections.append(f"- Uncommitted files: {len(git_status.uncommitted_files)}")
        if git_status.recent_commits:
            sections.append("\nRecent commits:")
            for commit in git_status.recent_commits[:3]:
                sections.append(f"  - {commit}")
        sections.append("")

    # File tree
    file_tree = get_file_tree(cwd, max_depth=2)
    sections.append(f"**File Tree:**\n```\n{file_tree}\n```\n")

    # Environment
    sections.append("**Environment:**")
    sections.append(f"- OS: {platform.system()} {platform.release()}")
    sections.append(f"- Python: {sys.version.split()[0]}")
    sections.append("")

    return "\n".join(sections)
