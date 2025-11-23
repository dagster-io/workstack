"""Create worktree from GitHub issue with erk-plan label.

This kit CLI command provides deterministic worktree creation from GitHub issues,
replacing the non-deterministic agent-based workflow.

Usage:
    dot-agent run erk create-wt-from-issue <issue-number-or-url>

Output:
    User-friendly formatted output with next steps

Exit Codes:
    0: Success (worktree created)
    1: Error (parsing failed, issue not found, missing label, etc.)

Examples:
    $ dot-agent run erk create-wt-from-issue 776
    ✅ Worktree created from issue #776: **feature-name**

    Branch: `issue-776-25-11-22`
    Location: `/path/to/worktree`
    Plan: `.impl/plan.md`
    Issue: https://github.com/owner/repo/issues/776

    **Next step:**

    `erk checkout issue-776-25-11-22 && claude --permission-mode acceptEdits "/erk:implement-plan"`

    $ dot-agent run erk create-wt-from-issue https://github.com/owner/repo/issues/776
    (same as above)
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import click

from erk.core.impl_folder import save_issue_reference


def get_repo_root() -> Path | None:
    """Get repository root using git rev-parse.

    Returns:
        Path to repository root, or None if not in git repo
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


def parse_issue_reference(issue_arg: str) -> dict[str, str | int | bool]:
    """Parse issue reference using parse-issue-reference command.

    Args:
        issue_arg: Issue number or GitHub URL

    Returns:
        Dict with success, issue_number (if success), or error/message (if failure)
    """
    result = subprocess.run(
        ["dot-agent", "run", "erk", "parse-issue-reference", issue_arg],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        # Parse error response
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "parse_failed",
                "message": f"Failed to parse issue reference: {result.stderr}",
            }

    # Parse success response
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "invalid_json",
            "message": "Invalid JSON response from parse-issue-reference",
        }


def fetch_issue_from_github(issue_number: int) -> dict[str, Any] | None:
    """Fetch issue data from GitHub using gh CLI.

    Args:
        issue_number: GitHub issue number

    Returns:
        Dict with issue data, or None if fetch failed
    """
    result = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,title,body,state,url,labels",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def has_erk_plan_label(issue_data: dict[str, Any]) -> bool:
    """Check if issue has erk-plan label.

    Args:
        issue_data: Issue data from gh CLI

    Returns:
        True if erk-plan label present, False otherwise
    """
    labels = issue_data.get("labels", [])
    if not isinstance(labels, list):
        return False

    for label in labels:
        if isinstance(label, dict) and label.get("name") == "erk-plan":
            return True

    return False


def create_worktree_from_plan(
    plan_content: str, temp_dir: Path
) -> dict[str, str] | None:
    """Create worktree using erk create command.

    Args:
        plan_content: Plan markdown content
        temp_dir: Temporary directory for plan file

    Returns:
        Dict with worktree details (worktree_name, worktree_path, branch_name),
        or None if creation failed
    """
    temp_file = temp_dir / "plan.md"
    temp_file.write_text(plan_content, encoding="utf-8")

    result = subprocess.run(
        ["erk", "create", "--plan", str(temp_file), "--json", "--stay"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
        if data.get("status") == "success":
            return {
                "worktree_name": data.get("worktree_name"),
                "worktree_path": data.get("worktree_path"),
                "branch_name": data.get("branch_name"),
            }
        return None
    except json.JSONDecodeError:
        return None


def post_creation_comment(
    issue_number: int, worktree_name: str, branch_name: str
) -> bool:
    """Post worktree creation comment to GitHub issue.

    Args:
        issue_number: GitHub issue number
        worktree_name: Name of created worktree
        branch_name: Git branch name

    Returns:
        True if comment posted successfully, False otherwise
    """
    result = subprocess.run(
        [
            "dot-agent",
            "run",
            "erk",
            "comment-worktree-creation",
            str(issue_number),
            worktree_name,
            branch_name,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


@click.command()
@click.argument("issue_reference")
def create_wt_from_issue(issue_reference: str) -> None:
    """Create worktree from GitHub issue with erk-plan label.

    ISSUE_REFERENCE: GitHub issue number or full URL
    """
    # Step 1: Check if in git repository
    repo_root = get_repo_root()
    if repo_root is None:
        click.echo(click.style("Error: ", fg="red") + "Not in a git repository", err=True)
        raise SystemExit(1)

    # Step 2: Parse issue reference
    parse_result = parse_issue_reference(issue_reference)
    if not parse_result.get("success"):
        click.echo(
            click.style("Error: ", fg="red")
            + f"Failed to parse issue reference: {parse_result.get('message')}",
            err=True,
        )
        raise SystemExit(1)

    issue_number = int(parse_result["issue_number"])

    # Step 3: Fetch issue from GitHub
    issue_data = fetch_issue_from_github(issue_number)
    if issue_data is None:
        click.echo(
            click.style("Error: ", fg="red")
            + f"Failed to fetch issue #{issue_number} from GitHub. "
            + "Check that the issue exists and gh CLI is authenticated.",
            err=True,
        )
        raise SystemExit(1)

    # Step 4: Check for erk-plan label
    if not has_erk_plan_label(issue_data):
        labels = issue_data.get("labels", [])
        label_names = [
            label.get("name") for label in labels if isinstance(label, dict) and label.get("name")
        ]
        # Filter out None values and ensure all are strings
        label_names_str = [str(name) for name in label_names if name is not None]
        label_list = ", ".join(label_names_str) if label_names_str else "none"

        click.echo(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have the 'erk-plan' label.",
            err=True,
        )
        click.echo(f"Current labels: {label_list}", err=True)
        click.echo(
            "\nAdd the 'erk-plan' label to the issue and try again.", err=True
        )
        raise SystemExit(1)

    # Step 5: Extract plan from issue body
    body = issue_data.get("body", "")
    if not body or not body.strip():
        click.echo(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} has no body content",
            err=True,
        )
        raise SystemExit(1)

    # Step 6: Create worktree using temporary file
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        worktree_details = create_worktree_from_plan(body, temp_dir)

    if worktree_details is None:
        click.echo(
            click.style("Error: ", fg="red")
            + f"Failed to create worktree from issue #{issue_number}. "
            + "Check erk command output for details.",
            err=True,
        )
        raise SystemExit(1)

    worktree_name = worktree_details["worktree_name"]
    worktree_path = worktree_details["worktree_path"]
    branch_name = worktree_details["branch_name"]
    issue_url = str(issue_data.get("url", ""))

    # Step 7: Save issue reference to .impl/issue.json
    impl_dir = Path(worktree_path) / ".impl"
    if impl_dir.exists():
        try:
            save_issue_reference(impl_dir, issue_number, issue_url)
        except Exception as e:
            # Non-fatal: warn but don't fail
            click.echo(
                click.style("Warning: ", fg="yellow")
                + f"Failed to save issue reference: {e}",
                err=True,
            )

    # Step 8: Post GitHub comment (non-fatal)
    comment_posted = post_creation_comment(issue_number, worktree_name, branch_name)
    if not comment_posted:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post comment to issue #{issue_number}",
            err=True,
        )

    # Step 9: Display success output
    click.echo(f"✅ Worktree created from issue #{issue_number}: **{worktree_name}**")
    click.echo("")
    click.echo(f"Branch: `{branch_name}`")
    click.echo(f"Location: `{worktree_path}`")
    click.echo("Plan: `.impl/plan.md`")
    click.echo(f"Issue: {issue_url}")
    click.echo("")
    click.echo("**Next step:**")
    click.echo("")
    click.echo(
        f"`erk checkout {branch_name} && claude --permission-mode acceptEdits \"/erk:implement-plan\"`"
    )
