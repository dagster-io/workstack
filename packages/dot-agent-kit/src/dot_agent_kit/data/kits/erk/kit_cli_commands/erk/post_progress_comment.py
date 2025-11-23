"""Post GitHub issue progress comment with structured YAML.

This kit CLI command posts progress tracking comments to GitHub issues using
collapsible <details> sections with machine-parsable YAML data.

Usage:
    dot-agent run erk post-progress-comment --step-description "Phase 1: Create abstraction"

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk post-progress-comment --step-description "Phase 1 complete"
    {"success": true, "issue_number": 123, "progress": "3/5 (60%)"}

    $ dot-agent run erk post-progress-comment --step-description "Testing phase"
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from erk.core.impl_folder import parse_progress_frontmatter, read_issue_reference
from erk.integrations.github.metadata_blocks import (
    create_progress_status_block,
    render_erk_issue_event,
)


@dataclass(frozen=True)
class ProgressSuccess:
    """Success response for progress comment posting."""

    success: bool
    issue_number: int
    progress: str


@dataclass(frozen=True)
class ProgressError:
    """Error response for progress comment posting."""

    success: bool
    error_type: str
    message: str


@click.command(name="post-progress-comment")
@click.option("--step-description", required=True, help="Description of completed step")
@click.pass_context
def post_progress_comment(ctx: click.Context, step_description: str) -> None:
    """Post progress tracking comment to GitHub issue.

    Reads progress from .impl/progress.md frontmatter and posts a comment
    with structured YAML data in a collapsible details section.

    STEP_DESCRIPTION: Description of the step just completed
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)

    # Read issue reference
    impl_dir = Path.cwd() / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        result = ProgressError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Read progress file
    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        result = ProgressError(
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
        result = ProgressError(
            success=False,
            error_type="invalid_progress_format",
            message="Invalid YAML frontmatter in progress.md",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Extract progress data
    completed = frontmatter["completed_steps"]
    total = frontmatter["total_steps"]

    # Generate timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Create metadata block using shared library
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=completed,
        total_steps=total,
        timestamp=timestamp,
        step_description=step_description,
    )

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title=f"✓ Step {completed}/{total} completed",
        metadata=block,
        description="",
    )

    # Get GitHub Issues from context (with LBYL check)
    # Convert stderr error to JSON error for graceful degradation (|| true pattern)
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        result = ProgressError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Post comment to GitHub
    try:
        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
        percentage = int((completed / total) * 100) if total > 0 else 0
        result = ProgressSuccess(
            success=True,
            issue_number=issue_ref.issue_number,
            progress=f"{completed}/{total} ({percentage}%)",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
    except RuntimeError as e:
        result = ProgressError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
