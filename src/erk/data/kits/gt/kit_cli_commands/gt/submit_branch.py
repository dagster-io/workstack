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

Error Types:
    - no_branch: Could not determine current branch
    - no_parent: Could not determine parent branch
    - no_commits: No commits found in branch
    - squash_failed: Failed to squash commits
    - amend_failed: Failed to amend commit
    - submit_failed: Failed to submit branch (generic)
    - submit_timeout: Submit command timed out
    - submit_merged_parent: Parent branches merged but not in main trunk
    - submit_diverged: Branch has diverged from remote
    - submit_empty_parent: Stack contains empty parent branch (already merged)
    - pr_update_failed: Failed to update PR metadata

Examples:
    $ dot-agent run gt submit-pr pre-analysis
    {"success": true, "branch_name": "feature", ...}

    $ dot-agent run gt submit-pr post-analysis --commit-message "feat: add feature"
        --pr-title "Add feature" --pr-body "Full description"
    {"success": true, "pr_number": 123, ...}
"""

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, NamedTuple

import click
from erk_shared.env import in_github_actions
from erk_shared.impl_folder import (
    has_issue_reference,
    read_issue_reference,
    read_plan_author,
    read_run_info,
)

from erk.data.kits.gt.kit_cli_commands.gt.ops import GtKit
from erk.data.kits.gt.kit_cli_commands.gt.real_ops import RealGtKit


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


def get_diff_context(ops: GtKit | None = None) -> DiffContextResult:
    """Get all context needed for AI diff analysis.

    Args:
        ops: Optional ops implementation for testing

    Returns:
        DiffContextResult with repo root, branches, and diff

    Raises:
        ValueError: If no parent branch found
        subprocess.CalledProcessError: If git operations fail
    """
    if ops is None:
        ops = RealGtKit()

    # Get repository root
    repo_root = ops.git().get_repository_root()

    # Get current branch
    current_branch = ops.git().get_current_branch()
    if current_branch is None:
        raise ValueError("Could not determine current branch")

    # Get parent branch
    parent_branch = ops.graphite().get_parent_branch()
    if parent_branch is None:
        raise ValueError("No parent branch found - not in a Graphite stack")

    # Get full diff
    diff = ops.git().get_diff_to_parent(parent_branch)

    return DiffContextResult(
        success=True,
        repo_root=repo_root,
        current_branch=current_branch,
        parent_branch=parent_branch,
        diff=diff,
    )


def execute_pre_analysis(ops: GtKit | None = None) -> PreAnalysisResult | PreAnalysisError:
    """Execute the pre-analysis phase. Returns success or error result."""
    if ops is None:
        ops = RealGtKit()

    # Step 0a: Check Graphite authentication FIRST (before any git operations)
    click.echo("  ↳ Checking Graphite authentication...", err=True)
    gt_authenticated, gt_username, _ = ops.graphite().check_auth_status()
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
    click.echo(f"  ✓ Authenticated as {gt_username}", err=True)

    # Step 0b: Check GitHub authentication (required for PR operations)
    click.echo("  ↳ Checking GitHub authentication...", err=True)
    gh_authenticated, gh_username, _ = ops.github().check_auth_status()
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
    click.echo(f"  ✓ Authenticated as {gh_username}", err=True)

    # Step 0c: Check for and commit uncommitted changes
    uncommitted_changes_committed = False
    if ops.git().has_uncommitted_changes():
        click.echo("  ↳ Committing uncommitted changes...", err=True)
        if not ops.git().add_all():
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to stage uncommitted changes",
                details={"reason": "git add failed"},
            )
        if not ops.git().commit("WIP: Prepare for submission"):
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to commit uncommitted changes",
                details={"reason": "git commit failed"},
            )
        uncommitted_changes_committed = True
        click.echo("  ✓ Uncommitted changes committed", err=True)

    # Step 1: Get current branch
    branch_name = ops.git().get_current_branch()

    if branch_name is None:
        return PreAnalysisError(
            success=False,
            error_type="no_branch",
            message="Could not determine current branch",
            details={"branch_name": "unknown"},
        )

    # Step 2: Get parent branch
    parent_branch = ops.graphite().get_parent_branch()

    if parent_branch is None:
        return PreAnalysisError(
            success=False,
            error_type="no_parent",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"branch_name": branch_name},
        )

    # Step 2.5: Check for merge conflicts EARLY
    # First try GitHub API if PR exists (most accurate)
    # TODO: Move full GitHub implementations to erk-shared
    # Currently using erk-shared stub which raises NotImplementedError at runtime.
    # This is the correct architectural solution but requires refactoring to move
    # the complete RealGitHub implementation from erk.core.github.real.
    # Until then, PR status/mergeability checks will fail if actually invoked.
    try:
        from erk_shared.github.real import RealGitHub

        github = RealGitHub()
        repo_root = Path(ops.git().get_repository_root())
        pr_info = github.get_pr_status(repo_root, branch_name, debug=False)

        if pr_info.pr_number is not None:
            # PR exists - check mergeability
            mergeability = github.get_pr_mergeability(repo_root, pr_info.pr_number)

            if mergeability and mergeability.mergeable == "CONFLICTING":
                return PreAnalysisError(
                    success=False,
                    error_type="pr_has_conflicts",
                    message=f"PR #{pr_info.pr_number} has merge conflicts with {parent_branch}",
                    details={
                        "branch_name": branch_name,
                        "pr_number": str(pr_info.pr_number),
                        "parent_branch": parent_branch,
                        "merge_state": mergeability.merge_state_status,
                    },
                )

            # UNKNOWN status: proceed with warning (GitHub hasn't computed yet)
            if mergeability and mergeability.mergeable == "UNKNOWN":
                print(
                    "⚠️  Warning: PR mergeability status is UNKNOWN, proceeding anyway",
                    file=sys.stderr,
                )

        else:
            # No PR yet - fallback to local git merge-tree check
            if ops.git().check_merge_conflicts(parent_branch, branch_name):
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
    except (NotImplementedError, TypeError):
        # RealGitHub from erk-shared is a stub - skip GitHub-based conflict checking
        # Fall back to local git merge-tree check only
        if ops.git().check_merge_conflicts(parent_branch, branch_name):
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
    commit_count = ops.git().count_commits_in_branch(parent_branch)

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
        click.echo(f"  ↳ Squashing {commit_count} commits...", err=True)
        result = ops.graphite().squash_commits()
        if not result.success:
            # Check if failure was due to merge conflict
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

            # Generic squash failure (not conflict-related)
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
        click.echo(f"  ✓ Squashed {commit_count} commits into 1", err=True)

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


def build_pr_metadata_section(
    impl_dir: Path,
    pr_number: int | None = None,
) -> str:
    """Build metadata section for PR body.

    Args:
        impl_dir: Path to .impl/ directory
        pr_number: PR number (use None for placeholder)

    Returns:
        Metadata section as string (empty if no metadata exists)
    """
    issue_ref = read_issue_reference(impl_dir) if has_issue_reference(impl_dir) else None
    plan_author = read_plan_author(impl_dir)
    run_info = read_run_info(impl_dir)

    # Only build metadata if we have something to show
    if issue_ref is None and plan_author is None and run_info is None:
        return ""

    metadata_parts: list[str] = []

    # Opening sentence - only for erk-queue submissions running in CI
    # (not when locally re-submitting a PR that was originally created by the queue)
    if run_info is not None and in_github_actions():
        metadata_parts.append("This PR was generated by an agent in the `erk` queue.\n")

    # Bullets
    bullets: list[str] = []
    if issue_ref is not None:
        bullets.append(f"- **Plan:** [#{issue_ref.issue_number}]({issue_ref.issue_url})")
    if plan_author is not None:
        bullets.append(f"- **Plan Author:** @{plan_author}")
    if run_info is not None and in_github_actions():
        bullets.append(f"- **GitHub Action:** [View Run]({run_info.run_url})")

    if bullets:
        metadata_parts.append("\n".join(bullets) + "\n")

    # Checkout command (with placeholder or actual number)
    pr_display = str(pr_number) if pr_number is not None else "__PLACEHOLDER_PR_NUMBER__"
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_display}\n"
        f"```\n"
    )

    # Closes #N
    if issue_ref is not None:
        metadata_parts.append(f"\nCloses #{issue_ref.issue_number}\n")

    # Separator
    metadata_parts.append("\n---\n")

    return "\n".join(metadata_parts)


def _invoke_commit_message_agent(diff_context: DiffContextResult) -> str:
    """Invoke Claude directly to generate commit message from diff.

    Args:
        diff_context: Diff and repository context

    Returns:
        Generated commit message text

    Raises:
        RuntimeError: If Claude invocation fails
    """
    from erk.data.kits.gt.kit_cli_commands.gt.prompts import (
        COMMIT_MESSAGE_SYSTEM_PROMPT,
        truncate_diff,
    )

    # Truncate if needed
    diff_content, was_truncated = truncate_diff(diff_context.diff)

    truncation_note = ""
    if was_truncated:
        truncation_note = "\n**NOTE**: Diff truncated. Focus on visible changes.\n"

    # Build prompt with inline diff
    prompt = f"""Generate commit message for this diff.

Repository: {diff_context.repo_root}
Branch: {diff_context.current_branch} (parent: {diff_context.parent_branch})
{truncation_note}
```diff
{diff_content}
```

Return ONLY the commit message. First line = PR title, rest = PR body."""

    # Direct Claude invocation - no Task delegation
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--output-format",
            "text",
            "--model",
            "haiku",
            "--tools",
            "",  # No tools needed
            "--append-system-prompt",
            COMMIT_MESSAGE_SYSTEM_PROMPT,
            "--",
            prompt,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=diff_context.repo_root,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude failed: {result.stderr or 'Unknown error'}")

    if not result.stdout.strip():
        raise RuntimeError("Claude returned no output")

    return result.stdout.strip()


def orchestrate_submit_workflow(
    ops: GtKit | None = None,
) -> PostAnalysisResult | PostAnalysisError | PreAnalysisError:
    """Orchestrate complete PR submission with AI-generated PR metadata.

    Workflow (submit-first approach for reliability):
    1. Execute pre-analysis (squash commits, auth checks)
    2. Submit branch via Graphite (with existing commit message)
    3. Wait for PR to be created
    4. Get PR diff from GitHub API (accurate PR-specific diff)
    5. Generate PR title/body via AI
    6. Update PR metadata

    This approach is more reliable because:
    - The submit succeeds regardless of AI availability
    - Uses `gh pr diff` for accurate PR-specific diff (not git diff)
    - AI failure only affects cosmetic PR metadata, not the submission itself

    Args:
        ops: Optional GtKit for dependency injection (testing)

    Returns:
        Result or error from the workflow
    """
    if ops is None:
        ops = RealGtKit()

    # Step 1: Pre-analysis (squash commits, auth checks)
    click.echo("🔍 Running pre-analysis checks...", err=True)
    pre_result = execute_pre_analysis(ops)
    if isinstance(pre_result, PreAnalysisError):
        return pre_result
    click.echo("✓ Pre-analysis complete", err=True)

    # Step 2: Submit branch FIRST (with existing commit message)
    click.echo("🚀 Submitting PR...", err=True)
    submit_result = _execute_submit_only(ops)
    if isinstance(submit_result, PostAnalysisError):
        return submit_result
    click.echo("✓ Branch submitted", err=True)

    pr_number, pr_url, graphite_url, branch_name = submit_result

    # Step 3: Get PR diff from GitHub API (accurate PR-specific diff)
    click.echo("📊 Getting PR diff from GitHub...", err=True)
    try:
        pr_diff = ops.github().get_pr_diff(pr_number)
    except subprocess.CalledProcessError as e:
        # If we can't get diff, still return success but note the issue
        click.echo(f"⚠️  Could not get PR diff: {e}", err=True)
        pr_diff = None
    if pr_diff:
        click.echo("✓ PR diff retrieved", err=True)

    # Step 4: Generate PR title/body via AI (only if we have diff)
    pr_title: str | None = None
    pr_body: str | None = None

    if pr_diff:
        click.echo("🤖 Generating PR description via AI...", err=True)
        try:
            repo_root = ops.git().get_repository_root()
            current_branch = ops.git().get_current_branch() or branch_name
            parent_branch = ops.graphite().get_parent_branch() or "main"

            diff_context = DiffContextResult(
                success=True,
                repo_root=repo_root,
                current_branch=current_branch,
                parent_branch=parent_branch,
                diff=pr_diff,
            )
            commit_message = _invoke_commit_message_agent(diff_context)
            lines = commit_message.split("\n", 1)
            pr_title = lines[0]
            pr_body = lines[1].lstrip() if len(lines) > 1 else ""
            click.echo("✓ PR description generated", err=True)
        except RuntimeError as e:
            click.echo(f"⚠️  AI generation failed: {e}", err=True)
            # Continue without AI-generated content

    # Step 5: Update PR metadata (if we have AI-generated content)
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    if pr_title and pr_body is not None:
        click.echo("📝 Updating PR metadata...", err=True)
        metadata_section = build_pr_metadata_section(impl_dir, pr_number=pr_number)
        final_body = metadata_section + pr_body

        if ops.github().update_pr_metadata(pr_title, final_body):
            click.echo("✓ PR metadata updated", err=True)
        else:
            click.echo("⚠️  Failed to update PR metadata", err=True)

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
    ops: GtKit,
) -> tuple[int, str, str, str] | PostAnalysisError:
    """Submit branch and wait for PR info, without modifying commit message.

    Returns:
        Tuple of (pr_number, pr_url, graphite_url, branch_name) on success
        PostAnalysisError on failure
    """
    branch_name = ops.git().get_current_branch() or "unknown"

    # Submit branch
    click.echo("  ↳ Running gt submit (this may take a moment)...", err=True)
    result = ops.graphite().submit(publish=True, restack=True)

    # Check for empty parent branch
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

    click.echo("  ✓ Branch submitted to Graphite", err=True)

    # Wait for PR info
    pr_info = None
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]

    click.echo("⏳ Waiting for PR info from GitHub API...", err=True)

    for attempt in range(max_retries):
        if attempt > 0:
            click.echo(f"   Attempt {attempt + 1}/{max_retries}...", err=True)
        pr_info = ops.github().get_pr_info()
        if pr_info is not None:
            click.echo("✓ PR info retrieved", err=True)
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
    graphite_url_result = ops.github().get_graphite_pr_url(pr_number)
    graphite_url = graphite_url_result or ""

    return (pr_number, pr_url, graphite_url, branch_name)


def execute_post_analysis(
    commit_message: str, ops: GtKit | None = None
) -> PostAnalysisResult | PostAnalysisError:
    """Execute the post-analysis phase. Returns success or error result."""
    if ops is None:
        ops = RealGtKit()

    # Get impl directory first
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    # Read issue reference if present
    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    # Split AI commit message into title and body
    lines = commit_message.split("\n", 1)
    pr_title = lines[0]
    ai_body = lines[1].lstrip() if len(lines) > 1 else ""

    # Build metadata section with placeholder
    metadata_section = build_pr_metadata_section(impl_dir, pr_number=None)

    # Construct COMPLETE commit message (metadata + AI body)
    complete_commit_message = pr_title + "\n\n" + metadata_section + ai_body

    # Step 1: Get current branch for context
    branch_name = ops.git().get_current_branch()
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Amend commit with COMPLETE message (metadata included!)
    click.echo("  ↳ Amending commit with generated message...", err=True)
    if not ops.git().amend_commit(complete_commit_message):
        return PostAnalysisError(
            success=False,
            error_type="amend_failed",
            message="Failed to amend commit with new message",
            details={"branch_name": branch_name},
        )
    click.echo("  ✓ Commit amended", err=True)

    # Step 3: Submit branch
    click.echo("  ↳ Running gt submit (this may take a moment)...", err=True)
    result = ops.graphite().submit(publish=True, restack=True)

    # Check for empty parent branch (Graphite returns success but nothing submitted)
    # This MUST be checked even on success since gt returns exit code 0
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
        # Combine stdout and stderr for pattern matching
        combined_output = result.stdout + result.stderr
        combined_lower = combined_output.lower()

        # Check for merge conflicts during restack (MUST BE FIRST)
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

        # Check for merged parent branches not in main trunk
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

        # Check for branch divergence (updated remotely or must sync)
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

        # Check for timeout
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

        # Generic submit failure
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

    click.echo("  ✓ Branch submitted to Graphite", err=True)

    # Step 4: Check if PR exists (with retry for GitHub API delay)
    pr_info = None
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]

    click.echo("⏳ Waiting for PR info from GitHub API...", err=True)

    for attempt in range(max_retries):
        if attempt > 0:  # Don't print on first attempt
            click.echo(f"   Attempt {attempt + 1}/{max_retries}...", err=True)
        pr_info = ops.github().get_pr_info()
        if pr_info is not None:
            click.echo("✓ PR info retrieved", err=True)
            break
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])

    if pr_info is None:
        click.echo("❌ Failed to get PR info after all retries", err=True)

    # Step 5: Update PR metadata if PR exists
    pr_number = None
    pr_url = ""
    graphite_url = ""

    if pr_info is not None:
        pr_number, pr_url = pr_info

        # Get Graphite URL
        graphite_url_result = ops.github().get_graphite_pr_url(pr_number)
        if graphite_url_result is not None:
            graphite_url = graphite_url_result

        # Rebuild metadata section with actual PR number
        metadata_with_pr = build_pr_metadata_section(impl_dir, pr_number=pr_number)
        final_pr_body = metadata_with_pr + ai_body

        # Lightweight update (just replacing placeholder)
        if not ops.github().update_pr_metadata(pr_title, final_pr_body):
            # This is now truly optional - metadata already in PR
            click.echo(
                "⚠️  Note: PR created with metadata, but checkout command shows placeholder",
                err=True,
            )
            message = (
                f"Successfully submitted branch: {branch_name}\n"
                f"Created PR #{pr_number}: {pr_url}\n"
                "⚠️  Note: PR created with metadata, but checkout command shows placeholder"
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
    """Get all context needed for AI diff analysis.

    Returns JSON with:
    - repo_root: Absolute path to repository root
    - current_branch: Name of current branch
    - parent_branch: Name of parent branch
    - diff: Full diff output from parent to HEAD
    """
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
    """Orchestrate PR submission with AI-generated commit message.

    This command:
    1. Runs pre-analysis (auth, squash, conflicts)
    2. Extracts diff
    3. Invokes Claude agent to generate commit message
    4. Amends commit and submits PR

    All in Python - agent only generates the message.
    """
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
