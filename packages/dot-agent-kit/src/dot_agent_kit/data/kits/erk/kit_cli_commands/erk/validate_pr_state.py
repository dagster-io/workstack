"""Validate PR state before submission.

This kit CLI command checks if a branch has a PR with valid state
and detects branch name collisions between issues.

Usage:
    dot-agent run erk validate-pr-state --issue-number 123 --branch-name my-feature
    dot-agent run erk validate-pr-state --issue-number 123 --branch-name my-feature --post-comment

Output:
    JSON with validation status and PR info

Exit Codes:
    0: Success (PR is valid or doesn't exist)
    1: Validation error (closed/merged PR or branch collision)

Examples:
    $ dot-agent run erk validate-pr-state --issue-number 123 --branch-name feat
    {"valid": true, "pr_exists": false}

    $ dot-agent run erk validate-pr-state --issue-number 123 --branch-name feat
    {"valid": true, "pr_exists": true, "pr_state": "OPEN", "pr_number": 456}

    $ dot-agent run erk validate-pr-state --issue-number 123 --branch-name feat
    {"valid": false, "pr_exists": true, "pr_state": "CLOSED", ...}
"""

import json
import subprocess
from dataclasses import asdict, dataclass

import click


@dataclass
class ValidationResult:
    """Result of PR state validation."""

    valid: bool
    pr_exists: bool
    pr_number: int | None = None
    pr_state: str | None = None
    linked_issue: int | None = None
    error_type: str | None = None
    error: str | None = None


def _run_gh_command(args: list[str]) -> tuple[str, int]:
    """Run gh CLI command and return (stdout, returncode).

    Returns empty string and non-zero code on failure.
    """
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip(), result.returncode
    except FileNotFoundError:
        return "", 1


def _get_pr_info(branch_name: str) -> dict | None:
    """Get PR info for branch using gh CLI.

    Returns dict with number, state, or None if no PR exists.
    """
    stdout, code = _run_gh_command(["pr", "view", branch_name, "--json", "number,state"])
    if code != 0:
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _get_linked_issue(branch_name: str) -> int | None:
    """Get linked issue number from PR's closingIssuesReferences.

    Uses GraphQL API to query the PR's linked issues.
    Returns the first linked issue number, or None if not found.
    """
    # Get repo info for GraphQL query
    stdout, code = _run_gh_command(["repo", "view", "--json", "owner,name"])
    if code != 0:
        return None

    try:
        repo_info = json.loads(stdout)
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]
    except (json.JSONDecodeError, KeyError):
        return None

    # GraphQL query for closingIssuesReferences
    query = f"""query {{
  repository(owner: "{owner}", name: "{repo_name}") {{
    pullRequests(headRefName: "{branch_name}", first: 1) {{
      nodes {{
        closingIssuesReferences(first: 1) {{
          nodes {{
            number
          }}
        }}
      }}
    }}
  }}
}}"""

    stdout, code = _run_gh_command(["api", "graphql", "-f", f"query={query}"])
    if code != 0:
        return None

    try:
        data = json.loads(stdout)
        prs = data.get("data", {}).get("repository", {}).get("pullRequests", {}).get("nodes", [])
        if not prs:
            return None

        closing_refs = prs[0].get("closingIssuesReferences", {})
        nodes = closing_refs.get("nodes", [])
        if nodes:
            return nodes[0].get("number")
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    return None


def _post_comment(issue_number: int, body: str) -> bool:
    """Post comment to issue. Returns True on success."""
    _, code = _run_gh_command(["issue", "comment", str(issue_number), "--body", body])
    return code == 0


def validate_pr_state(
    issue_number: int,
    branch_name: str,
    *,
    post_comment: bool = False,
) -> ValidationResult:
    """Validate PR state for branch submission.

    Checks:
    1. If PR exists, is it OPEN (not CLOSED/MERGED)?
    2. If PR has linked issue, is it the same issue we're submitting?

    Args:
        issue_number: GitHub issue number being submitted
        branch_name: Branch name to check
        post_comment: If True, post error comment to issue on failure

    Returns:
        ValidationResult with validation status and details
    """
    # Check if PR exists for this branch
    pr_info = _get_pr_info(branch_name)

    if pr_info is None:
        # No PR exists - valid to proceed
        return ValidationResult(valid=True, pr_exists=False)

    pr_number = pr_info.get("number")
    pr_state = pr_info.get("state")

    # Get linked issue number
    linked_issue = _get_linked_issue(branch_name)

    # Check for branch collision (different issue)
    if linked_issue is not None and linked_issue != issue_number:
        error_msg = (
            f"Branch '{branch_name}' is already associated with issue #{linked_issue}. "
            f"This issue (#{issue_number}) would derive the same branch name. "
            "Please rename one of the issues to avoid collision."
        )

        if post_comment:
            comment_body = f"""**Branch Collision Detected**

Branch `{branch_name}` is already associated with issue #{linked_issue}.

This issue (#{issue_number}) derives the same branch name from its title.

**Resolution:** Rename one of the issues to generate a unique branch name."""
            _post_comment(issue_number, comment_body)

        return ValidationResult(
            valid=False,
            pr_exists=True,
            pr_number=pr_number,
            pr_state=pr_state,
            linked_issue=linked_issue,
            error_type="branch_collision",
            error=error_msg,
        )

    # Check PR state
    if pr_state in ("CLOSED", "MERGED"):
        state_lower = pr_state.lower()
        error_msg = (
            f"PR for branch '{branch_name}' is {pr_state}. "
            f"Cannot submit to a {state_lower} PR. "
            f"Options: Reopen the PR with 'gh pr reopen {branch_name}' "
            f"or delete the branch with 'git push origin --delete {branch_name}'"
        )

        if post_comment:
            comment_body = f"""**PR Already {pr_state}**

The PR for branch `{branch_name}` has been {state_lower}.

Cannot submit implementation to a {state_lower} PR.

**Options:**
- Reopen the PR: `gh pr reopen {branch_name}`
- Delete branch and retry: `git push origin --delete {branch_name}`"""
            _post_comment(issue_number, comment_body)

        return ValidationResult(
            valid=False,
            pr_exists=True,
            pr_number=pr_number,
            pr_state=pr_state,
            linked_issue=linked_issue,
            error_type="pr_closed" if pr_state == "CLOSED" else "pr_merged",
            error=error_msg,
        )

    # PR exists and is OPEN - valid
    return ValidationResult(
        valid=True,
        pr_exists=True,
        pr_number=pr_number,
        pr_state=pr_state,
        linked_issue=linked_issue,
    )


@click.command(name="validate-pr-state")
@click.option(
    "--issue-number",
    required=True,
    type=int,
    help="GitHub issue number being submitted",
)
@click.option(
    "--branch-name",
    required=True,
    type=str,
    help="Branch name to validate",
)
@click.option(
    "--post-comment",
    is_flag=True,
    help="Post error comment to issue on validation failure",
)
def validate_pr_state_cmd(
    issue_number: int,
    branch_name: str,
    post_comment: bool,
) -> None:
    """Validate PR state before submission.

    Checks if the branch has a valid PR state for submission:
    - If PR exists, must be OPEN (not CLOSED or MERGED)
    - If PR has linked issue, must match the issue being submitted

    Outputs JSON with validation results.
    Exits with code 1 on validation failure.
    """
    result = validate_pr_state(
        issue_number=issue_number,
        branch_name=branch_name,
        post_comment=post_comment,
    )

    # Output JSON result
    output = asdict(result)
    # Remove None values for cleaner output
    output = {k: v for k, v in output.items() if v is not None}
    click.echo(json.dumps(output))

    if not result.valid:
        raise SystemExit(1)
