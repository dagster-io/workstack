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
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.core.github.issues import RealGitHubIssues
from erk.core.plan_folder import parse_progress_frontmatter, read_issue_reference


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


def get_repo_root() -> Path | None:
    """Get repository root using git rev-parse.

    Returns:
        Path to repository root, or None if not in a git repo

    LBYL pattern: Check returncode before using stdout
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip())


@click.command(name="post-completion-comment")
@click.option("--summary", required=True, help="Brief implementation summary")
def post_completion_comment(summary: str) -> None:
    """Post completion tracking comment to GitHub issue.

    Reads progress from .plan/progress.md frontmatter and posts a completion
    comment with structured YAML data in a collapsible details section.

    Only posts if plan is 100% complete (completed_steps == total_steps).

    SUMMARY: Brief summary of implementation
    """
    # Get repo root (LBYL pattern)
    repo_root = get_repo_root()
    if repo_root is None:
        result = CompletionError(
            success=False,
            error_type="not_in_repo",
            message="Not in a git repository",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Read issue reference
    plan_dir = Path.cwd() / ".plan"
    issue_ref = read_issue_reference(plan_dir)
    if issue_ref is None:
        result = CompletionError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .plan/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Read progress file
    progress_file = plan_dir / "progress.md"
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

    # Escape summary for YAML (wrap in quotes to protect special chars)
    yaml_safe_summary = summary.replace('"', '\\"')

    # Format completion comment with details + YAML
    comment_body = f"""✅ Implementation complete

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: {total}
total_steps: {total}
summary: "{yaml_safe_summary}"
timestamp: "{timestamp}"
```
</details>"""

    # Post comment to GitHub
    try:
        github = RealGitHubIssues()
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
