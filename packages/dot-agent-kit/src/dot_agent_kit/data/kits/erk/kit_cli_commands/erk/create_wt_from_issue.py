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

# ==============================================================================
# ARCHITECTURE ISSUES AND PROPOSED REFACTORING
# ==============================================================================
#
# This file documents current problems with create_wt_from_issue.py and
# proposes a migration path to fake-driven-testing patterns. These comments
# serve as inline documentation for future refactoring work.
#
# CURRENT PROBLEMS
# ================
#
# 1. Procedural Architecture:
#    - Script-style with direct subprocess calls throughout
#    - No abstraction layer between business logic and external systems
#    - External dependencies embedded inline: git, dot-agent, gh, erk CLIs
#    - Business logic and I/O operations tightly coupled
#
# 2. Testing Issues:
#    - Heavy mock-based testing (706 lines, 23 tests)
#    - Every test requires 30+ lines of mock setup for 4-5 CLI tools
#    - Mock state inconsistency (no state maintained across calls)
#    - Cannot verify operations occurred in correct order
#    - Hard to test complex multi-step workflows
#    - 10-100x slower than in-memory fakes
#    - No reusability of test infrastructure
#    - Tests tightly coupled to subprocess implementation details
#
# 3. Doesn't Follow Established Patterns:
#    - erk codebase uses ABC/Real/Fake pattern extensively
#    - Examples: Git, GitHub, Graphite all have ABC + Real + Fake
#    - This file is an outlier with procedural subprocess-heavy code
#    - FakeGitHubIssues already exists in production code as precedent
#
# 4. Test Infrastructure Duplication:
#    - Mock setup repeated in every test (~30 lines per test)
#    - Example pattern problems:
#      ```python
#      def mock_run(cmd, *args, **kwargs):
#          result = MagicMock()
#          result.returncode = 0
#          if cmd[0] == "git":
#              result.stdout = str(tmp_path)
#          elif cmd[0] == "dot-agent" and "parse-issue-reference" in cmd:
#              result.stdout = json.dumps({"success": True, "issue_number": 123})
#          elif cmd[0] == "gh":
#              result.stdout = json.dumps({...issue data...})
#          # etc. (30+ lines)
#      ```
#    - No mutation tracking for assertions
#    - Can't verify call ordering
#    - State doesn't persist across subprocess calls
#
# CRITICAL FINDING: GITHUB INTERFACE REDUNDANCY
# ==============================================
#
# DotAgentGitHubCli is 100% redundant with GitHubIssues:
#
# - DotAgentGitHubCli has ONE method: create_issue(title, body, labels)
# - GitHubIssues has FIVE methods: create_issue, get_issue, add_comment,
#   list_issues, ensure_label_exists
# - Both call identical gh CLI command: `gh issue create --title --body --label`
# - Key difference: DotAgentGitHubCli uses LBYL (returns success flag),
#   GitHubIssues raises exceptions (EAFP, aligned with dignified Python)
#
# DotAgentContext holds BOTH interfaces unnecessarily:
# ```python
# @dataclass(frozen=True)
# class DotAgentContext:
#     github_cli: DotAgentGitHubCli      # Only has create_issue()
#     github_issues: GitHubIssues        # Already has create_issue() + more!
# ```
#
# Conclusion: DotAgentGitHubCli serves no unique purpose and should be removed.
#
# PROPOSED SOLUTION: FAKE-DRIVEN-TESTING PATTERN
# ===============================================
#
# Refactor to follow erk's established ABC/Real/Fake pattern with dependency
# injection. This aligns with the fake-driven-testing kit's 5-layer architecture.
#
# Extract Integration Classes:
# ---------------------------
# 1. Git operations → Reuse erk.core.git (ABC + Real + Fake already exist)
# 2. GitHub issues → Reuse erk.core.github.issues (ABC + Real + Fake exist)
# 3. Worktree creation → NEW erk.core.worktree (ABC + Real + Fake)
# 4. Issue parsing → NEW dot_agent_kit.integrations.issue_parser (ABC + Real + Fake)
# 5. Issue storage → NEW dot_agent_kit.integrations.issue_store (ABC + Real + Fake)
#
# Refactor Pattern:
# ----------------
# ```python
# # Before (procedural):
# @click.command()
# def create_wt_from_issue(issue_reference: str) -> None:
#     repo_root = get_repo_root()  # subprocess inside
#     parse_result = parse_issue_reference(issue_reference)  # subprocess inside
#     issue_data = fetch_issue_data(parse_result.issue_number)  # subprocess inside
#     # ... more subprocess calls ...
#
# # After (injected):
# def create_wt_from_issue_impl(
#     issue_reference: str,
#     *,
#     git: Git,
#     github: GitHubIssues,
#     worktree: WorktreeCreator,
#     issue_parser: IssueParser,
#     issue_store: IssueStore,
# ) -> WorktreeCreationResult:
#     """Pure business logic - no subprocess calls."""
#     repo_root = git.get_repo_root()  # No subprocess, just method call
#     parse_result = issue_parser.parse(issue_reference)  # In-memory operation
#     issue_data = github.get_issue(repo_root, parse_result.issue_number)
#     # ... pure logic, all I/O through injected interfaces ...
#     return WorktreeCreationResult(...)
#
# @click.command()
# def create_wt_from_issue(issue_reference: str) -> None:
#     """CLI entry point - constructs real dependencies."""
#     result = create_wt_from_issue_impl(
#         issue_reference,
#         git=RealGit(),
#         github=RealGitHubIssues(),
#         worktree=RealWorktreeCreator(),
#         issue_parser=RealIssueParser(),
#         issue_store=RealIssueStore(),
#     )
#     # Format and display result...
# ```
#
# Testing Pattern:
# ---------------
# ```python
# # Before (mock-based, 30+ lines):
# def test_create_worktree_success(mocker):
#     mock_run = mocker.patch("subprocess.run")
#     def mock_run_impl(cmd, *args, **kwargs):
#         result = MagicMock()
#         result.returncode = 0
#         if cmd[0] == "git":
#             result.stdout = str(tmp_path)
#         elif cmd[0] == "dot-agent":
#             result.stdout = json.dumps({"success": True, "issue_number": 123})
#         # ... 20 more lines ...
#     mock_run.side_effect = mock_run_impl
#     # ... test logic ...
#
# # After (fake-based, 5 lines):
# def test_create_worktree_success():
#     github = FakeGitHubIssues().with_issue(123, "title", "body", ["erk-plan"])
#     git = FakeGit().with_repo_root(Path("/repo"))
#     worktree = FakeWorktreeCreator()
#
#     result = create_wt_from_issue_impl(
#         "123",
#         git=git,
#         github=github,
#         worktree=worktree,
#         issue_parser=FakeIssueParser(),
#         issue_store=FakeIssueStore(),
#     )
#
#     assert result.success
#     assert worktree.created_worktrees[0].issue_number == 123
# ```
#
# Fake-Driven-Testing 5-Layer Architecture:
# -----------------------------------------
# Layer 5: Business Logic Integration Tests (5%) - Real systems, slow, smoke tests
# Layer 4: Business Logic Tests (70%) - Fakes, fast, majority of tests ⭐
# Layer 3: Pure Unit Tests (10%) - Zero dependencies, isolated utilities
# Layer 2: Integration Sanity Tests (10%) - Real + mocked, quick validation
# Layer 1: Fake Infrastructure Tests (5%) - Test fakes themselves
#
# Key Principles:
# - Thin integration layer (ABC/Real/Fake wraps external state)
# - Fast tests over fakes (70% of tests use in-memory fakes)
# - Constructor injection (inject dependencies, no global state)
# - Mutation tracking (fakes expose read-only properties for assertions)
# - Declarative setup (with_issue() methods for test data setup)
# - No I/O in fakes (everything in-memory)
#
# CONSOLIDATION STRATEGY
# ======================
#
# Move fakes from tests/ to production code (src/erk/core/*/fake.py):
# - Follows FakeGitHubIssues precedent (already in production code)
# - Enables sharing between erk and dot-agent-kit packages
# - dot-agent-kit depends on erk, imports extensively from erk.core
# - Can't import from tests/ but can import from src/
#
# Eliminate DotAgentGitHubCli in favor of unified GitHubIssues interface:
# - Remove github_cli field from DotAgentContext
# - Remove require_github_cli() helper function
# - Migrate kit CLI commands to use require_github_issues()
# - Delete obsolete DotAgentGitHubCli files (ABC + Real + Fake + tests)
#
# EXPECTED BENEFITS
# =================
#
# After refactoring to fake-driven-testing:
# - 50% less test code (706 → ~350 lines)
# - 10-100x faster tests (in-memory vs subprocess)
# - Follows established codebase patterns
# - Enables code reuse between packages
# - Better test isolation and reliability
# - Easier to test complex workflows
# - Mutation tracking for precise assertions
# - Declarative test setup (with_issue(), with_repo(), etc.)
#
# SEE ALSO
# ========
#
# - fake-driven-testing kit documentation (5-layer architecture)
# - erk.core.github.issues.FakeGitHubIssues (production fake precedent)
# - dignified-python-313 kit (LBYL vs EAFP patterns)
# - erk.core.git, erk.core.github, erk.core.graphite (ABC/Real/Fake examples)
#
# ==============================================================================

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


def create_worktree_from_plan(plan_content: str, temp_dir: Path) -> dict[str, str] | None:
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


def post_creation_comment(issue_number: int, worktree_name: str, branch_name: str) -> bool:
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
        click.echo("\nAdd the 'erk-plan' label to the issue and try again.", err=True)
        raise SystemExit(1)

    # Step 5: Extract plan from issue body
    body = issue_data.get("body", "")
    if not body or not body.strip():
        click.echo(
            click.style("Error: ", fg="red") + f"Issue #{issue_number} has no body content",
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
                click.style("Warning: ", fg="yellow") + f"Failed to save issue reference: {e}",
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
        f"`erk checkout {branch_name} && "
        f'claude --permission-mode acceptEdits "/erk:implement-plan"`'
    )
