"""Create git commit and submit current branch with Graphite (two-phase).

This script handles mechanical git/gh/gt operations for the submit-branch workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (pre-analysis):
1. Get current branch and parent branch
2. Count commits in branch (compared to parent)
3. Run gt squash to consolidate commits (only if 2+ commits)
4. Return branch info for AI analysis

Phase 2 (post-analysis):
1. Amend commit with AI-generated commit message
2. Submit branch with gt submit --publish --no-interactive --restack
3. Check if PR exists and update metadata (title, body)
4. Return PR info and status

Usage:
    dot-agent run gt submit-branch pre-analysis
    dot-agent run gt submit-branch post-analysis --commit-message "..."
        --pr-title "..." --pr-body "..."

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or operation failed)

Error Types:
    - no_branch: Could not determine current branch
    - no_parent: Could not determine parent branch
    - no_commits: No commits found in branch
    - squash_failed: Failed to squash commits
    - amend_failed: Failed to amend commit
    - submit_failed: Failed to submit branch
    - pr_update_failed: Failed to update PR metadata

Examples:
    $ dot-agent run gt submit-branch pre-analysis
    {"success": true, "branch_name": "feature", ...}

    $ dot-agent run gt submit-branch post-analysis --commit-message "feat: add feature"
        --pr-title "Add feature" --pr-body "Full description"
    {"success": true, "pr_number": 123, ...}
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Literal

import click

PreAnalysisErrorType = Literal[
    "no_branch",
    "no_parent",
    "no_commits",
    "squash_failed",
]

PostAnalysisErrorType = Literal[
    "amend_failed",
    "submit_failed",
    "pr_update_failed",
]


@dataclass
class PreAnalysisResult:
    """Success result from pre-analysis phase."""

    success: bool
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    message: str


@dataclass
class PreAnalysisError:
    """Error result from pre-analysis phase."""

    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]


@dataclass
class PostAnalysisResult:
    """Success result from post-analysis phase."""

    success: bool
    pr_number: int | None
    pr_url: str
    branch_name: str
    message: str


@dataclass
class PostAnalysisError:
    """Error result from post-analysis phase."""

    success: bool
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


def get_current_branch() -> str | None:
    """Get the name of the current branch. Returns None if command fails."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_parent_branch() -> str | None:
    """Get the parent branch using gt parent. Returns None if command fails."""
    result = subprocess.run(
        ["gt", "parent"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def count_commits_in_branch(parent_branch: str) -> int:
    """Count commits in current branch compared to parent. Returns 0 if command fails."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{parent_branch}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return 0

    count_str = result.stdout.strip()
    if not count_str:
        return 0

    return int(count_str)


def squash_commits() -> bool:
    """Run gt squash to consolidate commits. Returns True on success."""
    result = subprocess.run(
        ["gt", "squash"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def amend_commit(message: str) -> bool:
    """Amend the current commit with new message. Returns True on success."""
    result = subprocess.run(
        ["git", "commit", "--amend", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def run_gt_submit() -> bool:
    """Run gt submit with publish and restack flags. Returns True on success."""
    result = subprocess.run(
        ["gt", "submit", "--publish", "--no-interactive", "--restack"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def get_pr_info() -> tuple[int, str] | None:
    """Get PR number and URL for current branch. Returns (number, url) or None."""
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number,url"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    return (data["number"], data["url"])


def update_pr_metadata(title: str, body: str) -> bool:
    """Update PR title and body using gh pr edit. Returns True on success."""
    result = subprocess.run(
        ["gh", "pr", "edit", "--title", title, "--body", body],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def execute_pre_analysis() -> PreAnalysisResult | PreAnalysisError:
    """Execute the pre-analysis phase. Returns success or error result."""

    # Step 1: Get current branch
    branch_name = get_current_branch()

    if branch_name is None:
        return PreAnalysisError(
            success=False,
            error_type="no_branch",
            message="Could not determine current branch",
            details={"branch_name": "unknown"},
        )

    # Step 2: Get parent branch
    parent_branch = get_parent_branch()

    if parent_branch is None:
        return PreAnalysisError(
            success=False,
            error_type="no_parent",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"branch_name": branch_name},
        )

    # Step 3: Count commits in branch
    commit_count = count_commits_in_branch(parent_branch)

    if commit_count == 0:
        return PreAnalysisError(
            success=False,
            error_type="no_commits",
            message=f"No commits found in branch: {branch_name}",
            details={"branch_name": branch_name, "parent_branch": parent_branch},
        )

    # Step 4: Run gt squash only if 2+ commits
    squashed = False
    if commit_count >= 2:
        if not squash_commits():
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to squash commits",
                details={
                    "branch_name": branch_name,
                    "commit_count": str(commit_count),
                },
            )
        squashed = True

    # Build success message
    if squashed:
        message = (
            f"Pre-analysis complete for branch: {branch_name}\n"
            f"Squashed {commit_count} commits into 1"
        )
    else:
        message = (
            f"Pre-analysis complete for branch: {branch_name}\nSingle commit, no squash needed"
        )

    return PreAnalysisResult(
        success=True,
        branch_name=branch_name,
        parent_branch=parent_branch,
        commit_count=commit_count,
        squashed=squashed,
        message=message,
    )


def execute_post_analysis(
    commit_message: str, pr_title: str, pr_body: str
) -> PostAnalysisResult | PostAnalysisError:
    """Execute the post-analysis phase. Returns success or error result."""

    # Step 1: Get current branch for context
    branch_name = get_current_branch()
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Amend commit with AI-generated message
    if not amend_commit(commit_message):
        return PostAnalysisError(
            success=False,
            error_type="amend_failed",
            message="Failed to amend commit with new message",
            details={"branch_name": branch_name},
        )

    # Step 3: Submit branch
    if not run_gt_submit():
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit branch with gt submit",
            details={"branch_name": branch_name},
        )

    # Step 4: Check if PR exists
    pr_info = get_pr_info()

    # Step 5: Update PR metadata if PR exists
    pr_number = None
    pr_url = ""

    if pr_info is not None:
        pr_number, pr_url = pr_info

        if not update_pr_metadata(pr_title, pr_body):
            return PostAnalysisError(
                success=False,
                error_type="pr_update_failed",
                message=f"Submitted branch but failed to update PR #{pr_number} metadata",
                details={"branch_name": branch_name, "pr_number": str(pr_number)},
            )

        message = f"Successfully submitted branch: {branch_name}\nUpdated PR #{pr_number}: {pr_url}"
    else:
        message = f"Successfully submitted branch: {branch_name}\nPR created (number pending)"

    return PostAnalysisResult(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        branch_name=branch_name,
        message=message,
    )


@click.group()
def submit_branch() -> None:
    """Create git commit and submit current branch with Graphite (two-phase)."""
    pass


@click.command()
def pre_analysis() -> None:
    """Execute pre-analysis phase: commit changes and squash."""
    try:
        result = execute_pre_analysis()
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PreAnalysisError):
            raise SystemExit(1)

    except Exception as e:
        error = PreAnalysisError(
            success=False,
            error_type="squash_failed",
            message=f"Unexpected error during pre-analysis: {e}",
            details={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None


@click.command()
@click.option(
    "--commit-message",
    required=True,
    help="AI-generated commit message to use for the final commit",
)
@click.option(
    "--pr-title",
    required=True,
    help="Title for the pull request",
)
@click.option(
    "--pr-body",
    required=True,
    help="Body content for the pull request",
)
def post_analysis(commit_message: str, pr_title: str, pr_body: str) -> None:
    """Execute post-analysis phase: amend commit and submit branch."""
    try:
        result = execute_post_analysis(commit_message, pr_title, pr_body)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PostAnalysisError):
            raise SystemExit(1)

    except Exception as e:
        error = PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message=f"Unexpected error during post-analysis: {e}",
            details={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None


# Register subcommands
submit_branch.add_command(pre_analysis)
submit_branch.add_command(post_analysis)
