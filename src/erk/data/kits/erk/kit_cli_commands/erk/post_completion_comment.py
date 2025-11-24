"""Post GitHub issue completion comment with structured YAML.

This kit CLI command posts completion tracking comments to GitHub issues using
collapsible <details> sections with machine-parsable YAML data.

Usage:
    dot-agent run erk post-completion-comment --summary "Added feature X with tests"

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk post-completion-comment --summary "Implementation complete"
    {"success": true, "issue_number": 123}

    $ dot-agent run erk post-completion-comment --summary "Done"
    {"success": false, "error_type": "not_complete", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import (
    create_implementation_status_block,
    render_erk_issue_event,
)
from erk_shared.github.status_history import build_status_history
from erk_shared.impl_folder import parse_progress_frontmatter, read_issue_reference

from dot_agent_kit.context_helpers import (
    require_cwd,
    require_git,
    require_github,
    require_github_issues,
    require_repo_root,
)


@dataclass(frozen=True)
class CompletionSuccess:
    """Success response for completion comment posting."""

    success: bool
    issue_number: int


@dataclass(frozen=True)
class CompletionError:
    """Error response for completion comment posting."""

    success: bool
    error_type: str
    message: str


@click.command(name="post-completion-comment")
@click.option("--summary", required=True, help="Brief implementation summary")
@click.pass_context
def post_completion_comment(ctx: click.Context, summary: str) -> None:
    """Post completion tracking comment to GitHub issue.

    Reads progress from .impl/progress.md frontmatter and posts a completion
    comment with structured YAML data in a collapsible details section.

    Only posts if plan is 100% complete (completed_steps == total_steps).

    SUMMARY: Brief summary of implementation
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    require_github(ctx)
    cwd = require_cwd(ctx)

    # Read issue reference
    impl_dir = cwd / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        result = CompletionError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Read progress file
    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        result = CompletionError(
            success=False,
            error_type="no_progress_file",
            message=f"Progress file not found: {progress_file}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Parse progress frontmatter
    content = progress_file.read_text(encoding="utf-8")
    frontmatter = parse_progress_frontmatter(content)
    if frontmatter is None:
        result = CompletionError(
            success=False,
            error_type="invalid_progress_format",
            message="Invalid YAML frontmatter in progress.md",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Extract progress data
    completed = frontmatter["completed_steps"]
    total = frontmatter["total_steps"]

    # Verify completion status
    if completed != total:
        result = CompletionError(
            success=False,
            error_type="not_complete",
            message=f"Plan not finished: {completed}/{total} steps",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Generate timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Gather implementation artifacts from Git integration
    branch_name = git.get_current_branch(cwd)

    # Get current HEAD commit SHA using get_recent_commits
    recent_commits = git.get_recent_commits(cwd, limit=1)
    commit_sha = recent_commits[0]["sha"] if recent_commits else None

    worktree_path = str(cwd.resolve())

    # Get GitHub Issues from context (with LBYL check)
    # Convert stderr error to JSON error for graceful degradation (|| true pattern)
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        result = CompletionError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Build status history by fetching previous metadata blocks
    try:
        # Fetch all comments from the issue
        comment_bodies = github.get_issue_comments(repo_root, issue_ref.issue_number)
        status_history = build_status_history(comment_bodies, timestamp)
    except Exception:
        # If we can't fetch history, just include completion event
        status_history = build_status_history([], timestamp)

    # TODO: Get PR URL from GitHub integration
    # Need to add get_pr_url(repo_root: Path, pr_number: int) -> str | None to GitHub ABC
    # For now, leave pr_url as None (it's optional in the metadata block)
    pr_url = None

    # Create metadata block using shared library
    block = create_implementation_status_block(
        status="complete",
        completed_steps=total,
        total_steps=total,
        timestamp=timestamp,
        summary=summary,
        branch_name=branch_name,
        pr_url=pr_url,
        commit_sha=commit_sha,
        worktree_path=worktree_path,
        status_history=status_history,
    )

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title="✅ Implementation complete",
        metadata=block,
        description="",
    )

    # Post comment to GitHub
    try:
        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
        result = CompletionSuccess(
            success=True,
            issue_number=issue_ref.issue_number,
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
    except RuntimeError as e:
        result = CompletionError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
