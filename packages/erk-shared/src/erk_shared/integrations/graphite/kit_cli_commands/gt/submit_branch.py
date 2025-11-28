"""Create git commit and submit current branch with Graphite (two-phase).

This script handles mechanical git/gh/gt operations for the submit-branch workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (pre-analysis):
1. Check for and commit any uncommitted changes
2. Get current branch and parent branch
3. Count commits in branch (compared to parent)
4. Run gt squash to consolidate commits (only if 2+ commits)
5. Return branch info for AI analysis

Phase 2 (post-analysis):
1. Split commit message into PR title (first line) and body (remaining lines)
2. Amend commit with AI-generated commit message
3. Submit branch with gt submit --publish --no-interactive --restack
4. Check if PR exists and update metadata (title, body)
5. Return PR info and status

Usage:
    dot-agent run gt submit-pr pre-analysis
    dot-agent run gt submit-pr post-analysis --commit-message "..."

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or operation failed)
"""

import json
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, NamedTuple

import click

from erk_shared.env import in_github_actions
from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.impl_folder import (
    has_issue_reference,
    read_issue_reference,
    read_plan_author,
    read_run_info,
)
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.graphite.types import CommandResult


class SubmitResult(NamedTuple):
    """Result from running gt submit command."""

    success: bool
    stdout: str
    stderr: str


PreAnalysisErrorType = Literal[
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_parent",
    "no_commits",
    "squash_failed",
    "squash_conflict",
    "pr_has_conflicts",
]

PostAnalysisErrorType = Literal[
    "amend_failed",
    "submit_failed",
    "submit_timeout",
    "submit_merged_parent",
    "submit_diverged",
    "submit_conflict",
    "submit_empty_parent",
    "pr_update_failed",
    "claude_not_available",
    "ai_generation_failed",
]


@dataclass
class PreAnalysisResult:
    """Success result from pre-analysis phase."""

    success: bool
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    uncommitted_changes_committed: bool
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
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


@dataclass
class PostAnalysisError:
    """Error result from post-analysis phase."""

    success: bool
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


@dataclass
class DiffContextResult:
    """Result of getting diff context for AI analysis."""

    success: bool
    repo_root: str
    current_branch: str
    parent_branch: str
    diff: str

    def model_dump(self) -> dict[str, str | bool]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "repo_root": self.repo_root,
            "current_branch": self.current_branch,
            "parent_branch": self.parent_branch,
            "diff": self.diff,
        }


def _get_pr_info(github: GitHub, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR number and URL for a branch."""
    prs = github.get_prs_for_repo(repo_root, include_checks=False)
    if branch in prs:
        pr = prs[branch]
        return (pr.number, pr.url)
    return None


def get_diff_context(
    git: Git | None = None,
    graphite: Graphite | None = None,
    repo_root: Path | None = None,
) -> DiffContextResult:
    """Get all context needed for AI diff analysis."""
    if git is None:
        git = RealGit()
    if graphite is None:
        graphite = RealGraphite()
    if repo_root is None:
        repo_root = Path.cwd()

    repo_root_str = str(repo_root.resolve())

    current_branch = git.get_current_branch(repo_root)
    if current_branch is None:
        raise ValueError("Could not determine current branch")

    parent_branch = graphite.get_parent_branch(git, repo_root, current_branch)
    if parent_branch is None:
        raise ValueError("No parent branch found - not in a Graphite stack")

    diff = git.get_diff_to_parent(repo_root, parent_branch)

    return DiffContextResult(
        success=True,
        repo_root=repo_root_str,
        current_branch=current_branch,
        parent_branch=parent_branch,
        diff=diff,
    )


def _branch_name_to_title(branch_name: str) -> str:
    """Convert kebab-case branch name to readable title."""
    words = branch_name.replace("-", " ").replace("_", " ")
    return words.capitalize() if words else "PR submitted"


def execute_pre_analysis(
    git: Git | None = None,
    github: GitHub | None = None,
    graphite: Graphite | None = None,
    repo_root: Path | None = None,
) -> PreAnalysisResult | PreAnalysisError:
    """Execute the pre-analysis phase. Returns success or error result."""
    if git is None:
        git = RealGit()
    if github is None:
        github = RealGitHub()
    if graphite is None:
        graphite = RealGraphite()
    if repo_root is None:
        repo_root = Path.cwd()

    # Step 0a: Check Graphite authentication FIRST
    click.echo("  -> Checking Graphite authentication...", err=True)
    gt_authenticated, gt_username, _ = graphite.check_auth_status()
    if not gt_authenticated:
        return PreAnalysisError(
            success=False,
            error_type="gt_not_authenticated",
            message="Graphite CLI (gt) is not authenticated",
            details={
                "fix": "Run 'gt auth' to authenticate with Graphite",
                "authenticated": False,
            },
        )
    click.echo(f"  [ok] Authenticated as {gt_username}", err=True)

    # Step 0b: Check GitHub authentication
    click.echo("  -> Checking GitHub authentication...", err=True)
    gh_authenticated, gh_username, _ = github.check_auth_status()
    if not gh_authenticated:
        return PreAnalysisError(
            success=False,
            error_type="gh_not_authenticated",
            message="GitHub CLI (gh) is not authenticated",
            details={
                "fix": "Run 'gh auth login' to authenticate with GitHub",
                "authenticated": False,
            },
        )
    click.echo(f"  [ok] Authenticated as {gh_username}", err=True)

    # Step 0c: Check for and commit uncommitted changes
    uncommitted_changes_committed = False
    if git.has_uncommitted_changes(repo_root):
        click.echo("  -> Committing uncommitted changes...", err=True)
        if not git.add_all(repo_root):
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to stage uncommitted changes",
                details={"reason": "git add failed"},
            )
        if not git.commit(repo_root, "WIP: Prepare for submission"):
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to commit uncommitted changes",
                details={"reason": "git commit failed"},
            )
        uncommitted_changes_committed = True
        click.echo("  [ok] Uncommitted changes committed", err=True)

    # Step 1: Get current branch
    branch_name = git.get_current_branch(repo_root)

    if branch_name is None:
        return PreAnalysisError(
            success=False,
            error_type="no_branch",
            message="Could not determine current branch",
            details={"branch_name": "unknown"},
        )

    # Step 2: Get parent branch
    parent_branch = graphite.get_parent_branch(git, repo_root, branch_name)

    if parent_branch is None:
        return PreAnalysisError(
            success=False,
            error_type="no_parent",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"branch_name": branch_name},
        )

    # Step 2.5: Check for merge conflicts EARLY
    pr_number, pr_url = _get_pr_status(github, repo_root, branch_name)

    if pr_number is not None:
        mergeability = github.get_pr_mergeability(repo_root, pr_number)

        if mergeability is not None and mergeability.mergeable == "CONFLICTING":
            return PreAnalysisError(
                success=False,
                error_type="pr_has_conflicts",
                message=f"PR #{pr_number} has merge conflicts with {parent_branch}",
                details={
                    "branch_name": branch_name,
                    "pr_number": str(pr_number),
                    "parent_branch": parent_branch,
                    "merge_state": mergeability.merge_state_status,
                    "detection_method": "github_api",
                },
            )

        if mergeability is not None and mergeability.mergeable == "UNKNOWN":
            print(
                "[warn] PR mergeability status is UNKNOWN, proceeding anyway",
                file=sys.stderr,
            )

    else:
        if git.check_merge_conflicts(repo_root, parent_branch, branch_name):
            return PreAnalysisError(
                success=False,
                error_type="pr_has_conflicts",
                message=f"Branch has local merge conflicts with {parent_branch}",
                details={
                    "branch_name": branch_name,
                    "parent_branch": parent_branch,
                    "detection_method": "git_merge_tree",
                },
            )

    # Step 3: Count commits in branch
    commit_count = git.count_commits_in_branch(repo_root, parent_branch)

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
        click.echo(f"  -> Squashing {commit_count} commits...", err=True)
        result = graphite.squash_commits(repo_root)
        if not result.success:
            combined_output = result.stdout + result.stderr
            if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
                return PreAnalysisError(
                    success=False,
                    error_type="squash_conflict",
                    message="Merge conflicts detected while squashing commits",
                    details={
                        "branch_name": branch_name,
                        "commit_count": str(commit_count),
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to squash commits",
                details={
                    "branch_name": branch_name,
                    "commit_count": str(commit_count),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )
        squashed = True
        click.echo(f"  [ok] Squashed {commit_count} commits into 1", err=True)

    # Build success message
    message_parts = [f"Pre-analysis complete for branch: {branch_name}"]

    if uncommitted_changes_committed:
        message_parts.append("Committed uncommitted changes")

    if squashed:
        message_parts.append(f"Squashed {commit_count} commits into 1")
    else:
        message_parts.append("Single commit, no squash needed")

    message = "\n".join(message_parts)

    return PreAnalysisResult(
        success=True,
        branch_name=branch_name,
        parent_branch=parent_branch,
        commit_count=commit_count,
        squashed=squashed,
        uncommitted_changes_committed=uncommitted_changes_committed,
        message=message,
    )


def _get_pr_status(github: GitHub, repo_root: Path, branch: str) -> tuple[int | None, str | None]:
    """Get PR number and URL for a specific branch."""
    prs = github.get_prs_for_repo(repo_root, include_checks=False)
    if branch in prs:
        pr = prs[branch]
        return (pr.number, pr.url)
    return (None, None)


def build_pr_metadata_section(
    impl_dir: Path,
    pr_number: int | None = None,
) -> str:
    """Build metadata section for PR body."""
    issue_ref = read_issue_reference(impl_dir) if has_issue_reference(impl_dir) else None
    plan_author = read_plan_author(impl_dir)
    run_info = read_run_info(impl_dir)

    if issue_ref is None and plan_author is None and run_info is None:
        return ""

    metadata_parts: list[str] = []

    if run_info is not None and in_github_actions():
        metadata_parts.append("This PR was generated by an agent in the `erk` queue.\n")

    bullets: list[str] = []
    if issue_ref is not None:
        bullets.append(f"- **Plan:** [#{issue_ref.issue_number}]({issue_ref.issue_url})")
    if plan_author is not None:
        bullets.append(f"- **Plan Author:** @{plan_author}")
    if run_info is not None and in_github_actions():
        bullets.append(f"- **GitHub Action:** [View Run]({run_info.run_url})")

    if bullets:
        metadata_parts.append("\n".join(bullets) + "\n")

    pr_display = str(pr_number) if pr_number is not None else "__PLACEHOLDER_PR_NUMBER__"
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_display}\n"
        f"```\n"
    )

    if issue_ref is not None:
        metadata_parts.append(f"\nCloses #{issue_ref.issue_number}\n")

    metadata_parts.append("\n---\n")

    return "\n".join(metadata_parts)


def _validate_claude_availability() -> tuple[bool, str]:
    """Check if Claude CLI is available and executable."""
    import os
    import shutil

    claude_path = shutil.which("claude")
    if claude_path is None:
        return False, (
            "Claude CLI not found in PATH.\n"
            "Install from: https://claude.ai/download\n"
            "Or ensure ~/.local/bin is in PATH"
        )

    if not os.access(claude_path, os.X_OK):
        return False, f"Claude CLI found at {claude_path} but not executable"

    return True, ""


def _invoke_commit_message_agent(diff_context: DiffContextResult) -> str:
    """Invoke commit-message-generator agent with diff file."""
    import os
    import tempfile

    from erk_shared.integrations.graphite.prompts import truncate_diff

    diff_content, was_truncated = truncate_diff(diff_context.diff)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".diff", delete=False, dir="/tmp", encoding="utf-8"
    ) as f:
        diff_path = f.name
        f.write(diff_content)

    try:
        truncation_note = "**NOTE**: Diff truncated for size.\n" if was_truncated else ""
        prompt = f"""Analyze the git diff and generate a commit message.

{truncation_note}Diff file: {diff_path}
Repository root: {diff_context.repo_root}
Current branch: {diff_context.current_branch}
Parent branch: {diff_context.parent_branch}

Use the Read tool to load the diff file."""

        result = subprocess.run(
            [
                "claude",
                "--print",
                "--output-format",
                "text",
                "--agents",
                "commit-message-generator",
                "--",
                prompt,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            cwd=diff_context.repo_root,
        )

        click.echo(f"   Claude exit code: {result.returncode}", err=True)
        if result.returncode != 0:
            click.echo(
                f"   Stderr: {result.stderr[:200] if result.stderr else '(empty)'}",
                err=True,
            )
            raise RuntimeError(f"Agent failed: {result.stderr or 'Unknown error'}")

        if not result.stdout.strip():
            click.echo("   Stdout length: 0 (no output generated)", err=True)
            raise RuntimeError("Agent returned no output")

        click.echo(f"   Stdout length: {len(result.stdout)} chars", err=True)
        return result.stdout.strip()

    finally:
        try:
            os.unlink(diff_path)
        except Exception:
            pass


def _run_gt_submit_with_progress(graphite: Graphite, repo_root: Path) -> CommandResult:
    """Run gt submit with descriptive progress markers."""
    start_time = time.time()
    result_holder: list[CommandResult] = []

    def run_submit():
        result_holder.append(graphite.submit(repo_root, publish=True, restack=False))

    thread = threading.Thread(target=run_submit, daemon=True)
    thread.start()

    progress_markers = [
        (10, "Pushing to remote"),
        (20, "Creating PR"),
        (30, "Finalizing"),
    ]

    marker_idx = 0

    while thread.is_alive():
        elapsed = time.time() - start_time

        if marker_idx < len(progress_markers):
            threshold, description = progress_markers[marker_idx]
            if elapsed >= threshold:
                click.echo(
                    click.style(f"  ... [{int(elapsed)}s] {description}", dim=True),
                    err=True,
                )
                marker_idx += 1

        thread.join(timeout=1.0)

    return result_holder[0]


def orchestrate_submit_workflow(
    git: Git | None = None,
    github: GitHub | None = None,
    graphite: Graphite | None = None,
    repo_root: Path | None = None,
) -> PostAnalysisResult | PostAnalysisError | PreAnalysisError:
    """Orchestrate complete PR submission with AI-generated PR metadata."""
    if git is None:
        git = RealGit()
    if github is None:
        github = RealGitHub()
    if graphite is None:
        graphite = RealGraphite()
    if repo_root is None:
        repo_root = Path.cwd()

    # Step 1: Pre-analysis
    click.echo("[1/5] Running pre-analysis checks...", err=True)
    pre_result = execute_pre_analysis(git, github, graphite, repo_root)
    if isinstance(pre_result, PreAnalysisError):
        return pre_result
    click.echo("[ok] Pre-analysis complete", err=True)

    # Step 2: Submit branch FIRST
    click.echo("[2/5] Submitting PR...", err=True)
    submit_start = time.time()
    submit_result = _execute_submit_only(git, github, graphite, repo_root)
    if isinstance(submit_result, PostAnalysisError):
        return submit_result
    submit_elapsed = int(time.time() - submit_start)
    click.echo(f"[ok] Branch submitted ({submit_elapsed}s)", err=True)

    pr_number, pr_url, graphite_url, branch_name = submit_result

    # Step 3: Get PR diff
    click.echo("[3/5] Getting PR diff from GitHub...", err=True)
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
    except subprocess.CalledProcessError as e:
        click.echo(f"[warn] Could not get PR diff: {e}", err=True)
        pr_diff = None
    if pr_diff:
        click.echo("[ok] PR diff retrieved", err=True)

    # Step 4: Generate PR title/body via AI
    pr_title: str | None = None
    pr_body: str | None = None

    if pr_diff:
        click.echo("[4/5] Checking Claude CLI availability...", err=True)
        available, error_msg = _validate_claude_availability()
        if not available:
            click.echo(f"[error] {error_msg}", err=True)
            return PostAnalysisError(
                success=False,
                error_type="claude_not_available",
                message="Claude CLI is not available",
                details={"error": error_msg},
            )

        click.echo("[ok] Claude CLI available", err=True)
        click.echo("[4/5] Generating PR description via AI...", err=True)
        try:
            repo_root_str = str(repo_root.resolve())
            current_branch = git.get_current_branch(repo_root) or branch_name
            parent_branch = graphite.get_parent_branch(git, repo_root, current_branch) or "main"

            diff_context = DiffContextResult(
                success=True,
                repo_root=repo_root_str,
                current_branch=current_branch,
                parent_branch=parent_branch,
                diff=pr_diff,
            )
            commit_message = _invoke_commit_message_agent(diff_context)
            lines = commit_message.split("\n", 1)
            pr_title = lines[0]
            pr_body = lines[1].lstrip() if len(lines) > 1 else ""
            click.echo("[ok] PR description generated", err=True)
        except Exception as e:
            error_type = type(e).__name__

            if isinstance(e, FileNotFoundError):
                diagnostic = "Claude CLI not found in PATH"
                suggestion = "Install Claude CLI: https://claude.ai/download"
            elif isinstance(e, PermissionError):
                diagnostic = "Claude CLI not executable"
                suggestion = "Check file permissions for claude binary"
            elif isinstance(e, subprocess.TimeoutExpired):
                diagnostic = "Claude invocation timed out"
                suggestion = "Check network connectivity or try again"
            else:
                diagnostic = str(e)
                suggestion = "Check session logs for details"

            click.echo(f"[error] AI generation failed: {error_type}", err=True)
            click.echo(f"   Diagnostic: {diagnostic}", err=True)
            click.echo(f"   Suggestion: {suggestion}", err=True)

            return PostAnalysisError(
                success=False,
                error_type="ai_generation_failed",
                message=f"AI generation failed: {error_type}",
                details={"error": diagnostic, "suggestion": suggestion},
            )

    # Step 5: Update PR metadata
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    click.echo("[5/5] Updating PR metadata...", err=True)
    metadata_section = build_pr_metadata_section(impl_dir, pr_number=pr_number)

    final_title = pr_title if pr_title else _branch_name_to_title(branch_name)
    final_body = metadata_section + (pr_body if pr_body else "")

    if github.update_pr_metadata(repo_root, pr_number, final_title, final_body):
        click.echo("[ok] PR metadata updated", err=True)
    else:
        click.echo("[warn] Failed to update PR metadata", err=True)

    return PostAnalysisResult(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_title=pr_title or "PR submitted",
        graphite_url=graphite_url,
        branch_name=branch_name,
        issue_number=issue_number,
        message=f"Successfully submitted branch: {branch_name}\nUpdated PR #{pr_number}: {pr_url}",
    )


def _execute_submit_only(
    git: Git,
    github: GitHub,
    graphite: Graphite,
    repo_root: Path,
) -> tuple[int, str, str, str] | PostAnalysisError:
    """Submit branch and wait for PR info, without modifying commit message."""
    branch_name = git.get_current_branch(repo_root) or "unknown"

    # Phase 1: Restack the stack
    click.echo("  -> Rebasing stack...", err=True)
    restack_start = time.time()
    restack_result = graphite.restack_with_result(repo_root)

    if not restack_result.success:
        combined_output = restack_result.stdout + restack_result.stderr
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during stack rebase",
                details={
                    "branch_name": branch_name,
                    "stdout": restack_result.stdout,
                    "stderr": restack_result.stderr,
                },
            )

        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to restack branch",
            details={
                "branch_name": branch_name,
                "stdout": restack_result.stdout,
                "stderr": restack_result.stderr,
            },
        )

    restack_elapsed = int(time.time() - restack_start)
    click.echo(f"  [ok] Stack rebased ({restack_elapsed}s)", err=True)

    # Phase 2: Submit to GitHub
    click.echo("  -> Pushing branches and creating PR...", err=True)
    result = _run_gt_submit_with_progress(graphite, repo_root)

    combined_output = result.stdout + result.stderr
    nothing_to_submit = "Nothing to submit!" in combined_output
    no_changes = "does not introduce any changes" in combined_output
    if nothing_to_submit or no_changes:
        return PostAnalysisError(
            success=False,
            error_type="submit_empty_parent",
            message=(
                "Stack contains an empty parent branch that was already merged. "
                "Run 'gt track --parent <trunk>' to reparent this branch, then 'gt restack'."
            ),
            details={
                "branch_name": branch_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    if not result.success:
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during branch submission",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "merged but the merged commits are not contained" in combined_output:
            return PostAnalysisError(
                success=False,
                error_type="submit_merged_parent",
                message="Parent branches have been merged but are not in main trunk",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "updated remotely" in combined_lower or "must sync" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_diverged",
                message="Branch has diverged from remote - manual sync required",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "timed out after 120 seconds" in result.stderr:
            return PostAnalysisError(
                success=False,
                error_type="submit_timeout",
                message=(
                    "gt submit timed out after 120 seconds. "
                    "Check network connectivity and try again."
                ),
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit branch with gt submit",
            details={
                "branch_name": branch_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    click.echo("  [ok] Branch submitted to Graphite", err=True)

    # Wait for PR info
    pr_info = None
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]

    click.echo("[...] Waiting for PR info from GitHub API...", err=True)

    for attempt in range(max_retries):
        if attempt > 0:
            click.echo(f"   Attempt {attempt + 1}/{max_retries}...", err=True)
        pr_info = _get_pr_info(github, repo_root, branch_name)
        if pr_info is not None:
            click.echo("[ok] PR info retrieved", err=True)
            break
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])

    if pr_info is None:
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="PR was submitted but could not retrieve PR info from GitHub",
            details={"branch_name": branch_name},
        )

    pr_number, pr_url = pr_info
    graphite_url_result = github.get_graphite_pr_url(repo_root, pr_number)
    graphite_url = graphite_url_result or ""

    return (pr_number, pr_url, graphite_url, branch_name)


def execute_post_analysis(
    commit_message: str,
    git: Git | None = None,
    github: GitHub | None = None,
    graphite: Graphite | None = None,
    repo_root: Path | None = None,
) -> PostAnalysisResult | PostAnalysisError:
    """Execute the post-analysis phase. Returns success or error result."""
    if git is None:
        git = RealGit()
    if github is None:
        github = RealGitHub()
    if graphite is None:
        graphite = RealGraphite()
    if repo_root is None:
        repo_root = Path.cwd()

    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    lines = commit_message.split("\n", 1)
    pr_title = lines[0]
    ai_body = lines[1].lstrip() if len(lines) > 1 else ""

    metadata_section = build_pr_metadata_section(impl_dir, pr_number=None)
    complete_commit_message = pr_title + "\n\n" + metadata_section + ai_body

    branch_name = git.get_current_branch(repo_root)
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Amend commit
    click.echo("  -> Amending commit with generated message...", err=True)
    if not git.amend_commit(repo_root, complete_commit_message):
        return PostAnalysisError(
            success=False,
            error_type="amend_failed",
            message="Failed to amend commit with new message",
            details={"branch_name": branch_name},
        )
    click.echo("  [ok] Commit amended", err=True)

    # Step 3a: Restack
    click.echo("  -> Rebasing stack...", err=True)
    restack_start = time.time()
    restack_result = graphite.restack_with_result(repo_root)

    if not restack_result.success:
        combined_output = restack_result.stdout + restack_result.stderr
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during stack rebase",
                details={
                    "branch_name": branch_name,
                    "stdout": restack_result.stdout,
                    "stderr": restack_result.stderr,
                },
            )

        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to restack branch",
            details={
                "branch_name": branch_name,
                "stdout": restack_result.stdout,
                "stderr": restack_result.stderr,
            },
        )

    restack_elapsed = int(time.time() - restack_start)
    click.echo(f"  [ok] Stack rebased ({restack_elapsed}s)", err=True)

    # Step 3b: Submit
    click.echo("  -> Submitting to GitHub...", err=True)
    result = graphite.submit(repo_root, publish=True, restack=False)

    combined_output = result.stdout + result.stderr
    nothing_to_submit = "Nothing to submit!" in combined_output
    no_changes = "does not introduce any changes" in combined_output
    if nothing_to_submit or no_changes:
        return PostAnalysisError(
            success=False,
            error_type="submit_empty_parent",
            message=(
                "Stack contains an empty parent branch that was already merged. "
                "Run 'gt track --parent <trunk>' to reparent this branch, then 'gt restack'."
            ),
            details={
                "branch_name": branch_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    if not result.success:
        combined_output = result.stdout + result.stderr
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during branch submission",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "merged but the merged commits are not contained" in combined_output:
            return PostAnalysisError(
                success=False,
                error_type="submit_merged_parent",
                message="Parent branches have been merged but are not in main trunk",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "updated remotely" in combined_lower or "must sync" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_diverged",
                message="Branch has diverged from remote - manual sync required",
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        if "timed out after 120 seconds" in result.stderr:
            return PostAnalysisError(
                success=False,
                error_type="submit_timeout",
                message=(
                    "gt submit timed out after 120 seconds. "
                    "Check network connectivity and try again."
                ),
                details={
                    "branch_name": branch_name,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit branch with gt submit",
            details={
                "branch_name": branch_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    click.echo("  [ok] Branch submitted to Graphite", err=True)

    # Step 4: Get PR info
    pr_info = None
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]

    click.echo("[...] Waiting for PR info from GitHub API...", err=True)

    for attempt in range(max_retries):
        if attempt > 0:
            click.echo(f"   Attempt {attempt + 1}/{max_retries}...", err=True)
        pr_info = _get_pr_info(github, repo_root, branch_name)
        if pr_info is not None:
            click.echo("[ok] PR info retrieved", err=True)
            break
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])

    if pr_info is None:
        click.echo("[error] Failed to get PR info after all retries", err=True)

    # Step 5: Update PR metadata
    pr_number = None
    pr_url = ""
    graphite_url = ""

    if pr_info is not None:
        pr_number, pr_url = pr_info

        graphite_url_result = github.get_graphite_pr_url(repo_root, pr_number)
        if graphite_url_result is not None:
            graphite_url = graphite_url_result

        metadata_with_pr = build_pr_metadata_section(impl_dir, pr_number=pr_number)
        final_pr_body = metadata_with_pr + ai_body

        if not github.update_pr_metadata(repo_root, pr_number, pr_title, final_pr_body):
            click.echo(
                "[warn] PR created with metadata, but checkout command shows placeholder",
                err=True,
            )
            message = (
                f"Successfully submitted branch: {branch_name}\n"
                f"Created PR #{pr_number}: {pr_url}\n"
                "[warn] PR created with metadata, but checkout command shows placeholder"
            )
        else:
            message = (
                f"Successfully submitted branch: {branch_name}\nUpdated PR #{pr_number}: {pr_url}"
            )
    else:
        message = f"Successfully submitted branch: {branch_name}\nPR created (number pending)"

    return PostAnalysisResult(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_title=pr_title,
        graphite_url=graphite_url,
        branch_name=branch_name,
        issue_number=issue_number,
        message=message,
    )


@click.group()
def pr_submit() -> None:
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
    help="AI-generated commit message (first line becomes PR title, rest becomes body)",
)
def post_analysis(commit_message: str) -> None:
    """Execute post-analysis phase: amend commit and submit branch."""
    try:
        result = execute_post_analysis(commit_message)
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


@click.command()
def get_diff_context_cmd() -> None:
    """Get all context needed for AI diff analysis."""
    try:
        result = get_diff_context()
        click.echo(json.dumps(result.model_dump()))

    except Exception as e:
        error_result = {
            "success": False,
            "error_type": "diff_context_failed",
            "message": str(e),
        }
        click.echo(json.dumps(error_result))
        raise SystemExit(1) from None


@click.command()
def orchestrate() -> None:
    """Orchestrate PR submission with AI-generated commit message."""
    try:
        result = orchestrate_submit_workflow()
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, (PreAnalysisError, PostAnalysisError)):
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


# Register subcommands
pr_submit.add_command(pre_analysis)
pr_submit.add_command(post_analysis)
pr_submit.add_command(get_diff_context_cmd, name="get-diff-context")
pr_submit.add_command(orchestrate)
