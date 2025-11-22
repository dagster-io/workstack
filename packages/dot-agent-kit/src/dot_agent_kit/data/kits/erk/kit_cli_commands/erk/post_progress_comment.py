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
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.core.github.issues import RealGitHubIssues
from erk.core.impl_folder import parse_progress_frontmatter, read_issue_reference


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


@click.command(name="post-progress-comment")
@click.option("--step-description", required=True, help="Description of completed step")
def post_progress_comment(step_description: str) -> None:
    """Post progress tracking comment to GitHub issue.

    Reads progress from .impl/progress.md frontmatter and posts a comment
    with structured YAML data in a collapsible details section.

    STEP_DESCRIPTION: Description of the step just completed
    """
    # Get repo root (LBYL pattern)
    repo_root = get_repo_root()
    if repo_root is None:
        result = ProgressError(
            success=False,
            error_type="not_in_repo",
            message="Not in a git repository",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

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
    percentage = int((completed / total) * 100) if total > 0 else 0

    # Generate timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Escape step_description for YAML (wrap in quotes to protect special chars)
    yaml_safe_description = step_description.replace('"', '\\"')

    # Format comment with details + YAML
    comment_body = f"""✓ Step {completed}/{total} completed

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: in_progress
completed_steps: {completed}
total_steps: {total}
percentage: {percentage}
step_description: "{yaml_safe_description}"
timestamp: "{timestamp}"
```
</details>"""

    # Post comment to GitHub
    try:
        github = RealGitHubIssues()
        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
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
