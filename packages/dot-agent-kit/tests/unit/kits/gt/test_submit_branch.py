"""Tests for submit_branch kit CLI command using fake ops."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    ERK_COMMIT_MESSAGE_MARKER,
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
    _branch_name_to_title,
    _is_valid_commit_message,
    _strip_commit_message_marker,
    build_pr_metadata_section,
    execute_post_analysis,
    execute_pre_analysis,
    orchestrate_submit_workflow,
    pr_submit,
)

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


def extract_json_from_output(output: str) -> dict:
    """Extract JSON object from CLI output that may contain styled messages.

    The CLI outputs styled messages (with ↳, ✓, etc.) followed by JSON.
    This function finds and parses the JSON portion.
    """
    # Find the start of JSON (first '{')
    json_start = output.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON found in output: {output}")

    # Find matching closing brace
    brace_count = 0
    for i, char in enumerate(output[json_start:], start=json_start):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_str = output[json_start : i + 1]
                return json.loads(json_str)

    raise ValueError(f"No complete JSON found in output: {output}")


class TestBranchNameToTitle:
    """Tests for _branch_name_to_title() function."""

    def test_converts_kebab_case_to_title(self) -> None:
        """Test converting kebab-case branch name to readable title."""
        assert _branch_name_to_title("fix-user-auth-bug") == "Fix user auth bug"

    def test_converts_underscores_to_spaces(self) -> None:
        """Test converting underscores to spaces."""
        assert _branch_name_to_title("add_new_feature") == "Add new feature"

    def test_handles_mixed_separators(self) -> None:
        """Test handling mixed hyphens and underscores."""
        assert _branch_name_to_title("fix-user_auth-bug") == "Fix user auth bug"

    def test_handles_empty_string(self) -> None:
        """Test handling empty branch name."""
        assert _branch_name_to_title("") == "PR submitted"

    def test_capitalizes_first_letter(self) -> None:
        """Test that only the first letter is capitalized."""
        assert _branch_name_to_title("UPPERCASE-BRANCH") == "Uppercase branch"


class TestIsValidCommitMessage:
    """Tests for _is_valid_commit_message() function.

    This function validates that the output contains the erk-generated commit
    message marker, providing deterministic validation.
    """

    def test_valid_message_with_marker(self) -> None:
        """Test that a message with the marker is accepted."""
        message = f"Add user authentication feature\n\n{ERK_COMMIT_MESSAGE_MARKER}"
        assert _is_valid_commit_message(message)

    def test_valid_message_with_marker_in_middle(self) -> None:
        """Test that marker in middle of message is accepted."""
        message = f"Title\n\nBody text\n\n{ERK_COMMIT_MESSAGE_MARKER}\n\nMore text"
        assert _is_valid_commit_message(message)

    def test_rejects_message_without_marker(self) -> None:
        """Test that a message without the marker is rejected."""
        assert not _is_valid_commit_message("Add user authentication feature")
        assert not _is_valid_commit_message("feat: add login functionality")
        assert not _is_valid_commit_message("")

    def test_rejects_permission_request_without_marker(self) -> None:
        """Test that permission requests (without marker) are rejected."""
        # This is the pattern from PR #1478 where Claude asked for permission
        permission_request = (
            "I need permission to read that file. "
            "Could you either:\n"
            "1. Grant me permission to read files from `/tmp/`\n"
            "2. Or share the diff content directly?"
        )
        assert not _is_valid_commit_message(permission_request)

    def test_marker_constant_value(self) -> None:
        """Test that the marker constant has the expected value."""
        assert ERK_COMMIT_MESSAGE_MARKER == "<!-- erk-generated commit message -->"


class TestStripCommitMessageMarker:
    """Tests for _strip_commit_message_marker() function."""

    def test_strips_marker_at_end(self) -> None:
        """Test that marker at end of message is stripped."""
        message = f"Add feature\n\nBody text\n\n{ERK_COMMIT_MESSAGE_MARKER}"
        result = _strip_commit_message_marker(message)
        assert result == "Add feature\n\nBody text"

    def test_strips_marker_on_own_line(self) -> None:
        """Test that marker on its own line is stripped."""
        message = f"Title\n\n{ERK_COMMIT_MESSAGE_MARKER}\n\nBody"
        result = _strip_commit_message_marker(message)
        # Marker line removed, empty lines before/after preserved
        assert result == "Title\n\n\nBody"

    def test_preserves_content_without_marker(self) -> None:
        """Test that content without marker is preserved."""
        message = "Title\n\nBody text"
        result = _strip_commit_message_marker(message)
        assert result == "Title\n\nBody text"

    def test_strips_trailing_whitespace(self) -> None:
        """Test that trailing whitespace after stripping is removed."""
        message = f"Title\n\n{ERK_COMMIT_MESSAGE_MARKER}\n\n"
        result = _strip_commit_message_marker(message)
        assert result == "Title"

    def test_handles_marker_with_surrounding_whitespace(self) -> None:
        """Test that marker with surrounding whitespace on line is stripped."""
        message = f"Title\n\n  {ERK_COMMIT_MESSAGE_MARKER}  \n\nBody"
        result = _strip_commit_message_marker(message)
        # Marker line (with whitespace) removed, empty lines preserved
        assert result == "Title\n\n\nBody"


class TestBuildPRMetadataSection:
    """Tests for build_pr_metadata_section() function."""

    def test_build_metadata_with_all_fields_in_ci(self, tmp_path: Path) -> None:
        """Test building metadata section with all fields in CI environment.

        When GITHUB_ACTIONS=true, the queue preamble and GitHub Action link should appear.
        """
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        # Create issue.json
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        # Create plan.md with author
        plan_md = impl_dir / "plan.md"
        plan_md.write_text(
            """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: testuser
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan
""",
            encoding="utf-8",
        )

        # Create run-info.json
        run_info_json = impl_dir / "run-info.json"
        run_info_json.write_text(
            '{"run_id": "12345678901", '
            '"run_url": "https://github.com/repo/actions/runs/12345678901"}',
            encoding="utf-8",
        )

        # Mock in_github_actions() to return True (simulating CI environment)
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.in_github_actions",
            return_value=True,
        ):
            result = build_pr_metadata_section(impl_dir, pr_number=456)

        assert "This PR was generated by an agent in the `erk` queue." in result
        assert "- **Plan:** [#123](https://github.com/repo/issues/123)" in result
        assert "- **Plan Author:** @testuser" in result
        assert (
            "- **GitHub Action:** [View Run](https://github.com/repo/actions/runs/12345678901)"
            in result
        )
        assert "erk pr checkout 456" in result
        assert "Closes #123" in result
        assert "---" in result

    def test_build_metadata_local_with_run_info_no_queue_preamble(self, tmp_path: Path) -> None:
        """Test that local submissions with run-info.json don't get queue preamble.

        When GITHUB_ACTIONS is not set (local submission), even if run-info.json exists
        (from a previous queue submission), the queue preamble and GitHub Action link
        should NOT appear.
        """
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        # Create issue.json
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        # Create plan.md with author
        plan_md = impl_dir / "plan.md"
        plan_md.write_text(
            """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: testuser
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan
""",
            encoding="utf-8",
        )

        # Create run-info.json (simulating checkout of a queue-originated branch)
        run_info_json = impl_dir / "run-info.json"
        run_info_json.write_text(
            '{"run_id": "12345678901", '
            '"run_url": "https://github.com/repo/actions/runs/12345678901"}',
            encoding="utf-8",
        )

        # Mock in_github_actions() to return False (simulating local submission)
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.in_github_actions",
            return_value=False,
        ):
            result = build_pr_metadata_section(impl_dir, pr_number=456)

        # Queue preamble and GitHub Action link should NOT appear
        assert "This PR was generated by an agent in the `erk` queue." not in result
        assert "- **GitHub Action:**" not in result
        # But other metadata should still appear
        assert "- **Plan:** [#123](https://github.com/repo/issues/123)" in result
        assert "- **Plan Author:** @testuser" in result
        assert "erk pr checkout 456" in result
        assert "Closes #123" in result
        assert "---" in result

    def test_build_metadata_with_placeholder(self, tmp_path: Path) -> None:
        """Test building metadata section with PR number placeholder."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        # Create issue.json
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 789, "issue_url": "https://github.com/repo/issues/789", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        result = build_pr_metadata_section(impl_dir, pr_number=None)

        assert "erk pr checkout __PLACEHOLDER_PR_NUMBER__" in result
        assert "Closes #789" in result

    def test_build_metadata_empty_when_no_metadata_files(self, tmp_path: Path) -> None:
        """Test that empty string is returned when no metadata files exist."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        result = build_pr_metadata_section(impl_dir, pr_number=456)

        assert result == ""

    def test_build_metadata_only_issue_reference(self, tmp_path: Path) -> None:
        """Test building metadata with only issue reference (no erk-queue message)."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 999, "issue_url": "https://github.com/repo/issues/999", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        result = build_pr_metadata_section(impl_dir, pr_number=100)

        assert "This PR was generated by an agent in the `erk` queue." not in result
        assert "- **Plan:** [#999](https://github.com/repo/issues/999)" in result
        assert "- **Plan Author:**" not in result
        assert "- **GitHub Action:**" not in result
        assert "erk pr checkout 100" in result
        assert "Closes #999" in result

    def test_build_metadata_only_plan_author(self, tmp_path: Path) -> None:
        """Test building metadata with only plan author (no erk-queue message)."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        plan_md = impl_dir / "plan.md"
        plan_md.write_text(
            """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: solo-author
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan
""",
            encoding="utf-8",
        )

        result = build_pr_metadata_section(impl_dir, pr_number=200)

        assert "This PR was generated by an agent in the `erk` queue." not in result
        assert "- **Plan Author:** @solo-author" in result
        assert "- **Plan:**" not in result
        assert "Closes #" not in result
        assert "erk pr checkout 200" in result


class TestPreAnalysisExecution:
    """Tests for pre-analysis phase execution logic."""

    def test_pre_analysis_gt_not_authenticated(self) -> None:
        """Test error when Graphite CLI is not authenticated."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "gt_not_authenticated"
        assert "Graphite CLI (gt) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gt auth' to authenticate with Graphite"
        assert result.details["authenticated"] is False

    def test_pre_analysis_gh_not_authenticated(self) -> None:
        """Test error when GitHub CLI is not authenticated (gt is authenticated)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gh_unauthenticated()
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "GitHub CLI (gh) is not authenticated" in result.message
        assert result.details["fix"] == "Run 'gh auth login' to authenticate with GitHub"
        assert result.details["authenticated"] is False

    def test_pre_analysis_gt_checked_before_gh(self) -> None:
        """Test that Graphite authentication is checked before GitHub."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
            .with_gh_unauthenticated()
        )

        result = execute_pre_analysis(ops)

        # When both are unauthenticated, gt should be reported first
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "gt_not_authenticated"

    def test_pre_analysis_with_uncommitted_changes(self) -> None:
        """Test pre-analysis when uncommitted changes exist (should commit them)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_commits(0)  # Start with no commits
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature-branch"
        assert result.uncommitted_changes_committed is True
        assert "Committed uncommitted changes" in result.message
        # After commit, should have 1 commit
        assert ops.git().count_commits_in_branch("main") == 1

    def test_pre_analysis_without_uncommitted_changes(self) -> None:
        """Test pre-analysis when no uncommitted changes exist."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)  # Single commit, no uncommitted files
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.uncommitted_changes_committed is False
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_pre_analysis_with_multiple_commits(self) -> None:
        """Test pre-analysis with 2+ commits (should squash)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.commit_count == 3
        assert result.squashed is True
        assert "Squashed 3 commits into 1" in result.message

    def test_pre_analysis_single_commit(self) -> None:
        """Test pre-analysis with single commit (no squash needed)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)  # Single commit
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.commit_count == 1
        assert result.squashed is False
        assert "Single commit, no squash needed" in result.message

    def test_pre_analysis_no_branch(self) -> None:
        """Test error when current branch cannot be determined."""
        ops = FakeGtKitOps()
        # Set current_branch to None to simulate failure
        from dataclasses import replace

        ops.git()._state = replace(ops.git().get_state(), current_branch="")

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "Could not determine current branch" in result.message

    def test_pre_analysis_no_parent(self) -> None:
        """Test error when parent branch cannot be determined."""
        ops = FakeGtKitOps().with_branch("orphan-branch", parent="main")
        # Remove parent relationship to simulate gt parent failure
        from dataclasses import replace

        gt_state = ops.graphite().get_state()
        ops.graphite()._state = replace(gt_state, branch_parents={})

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message

    def test_pre_analysis_no_commits(self) -> None:
        """Test error when branch has no commits."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(0)  # No commits
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "no_commits"
        assert "No commits found in branch" in result.message

    def test_pre_analysis_squash_fails(self) -> None:
        """Test error when gt squash fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits to trigger squash
            .with_squash_failure()  # Configure squash to fail
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "squash_failed"
        assert "Failed to squash commits" in result.message

    def test_pre_analysis_detects_squash_conflict(self) -> None:
        """Test that squash conflicts are detected and reported correctly."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits to trigger squash
            .with_squash_failure(
                stdout="",
                stderr=(
                    "error: could not apply abc123... commit message\n"
                    "CONFLICT (content): Merge conflict in file.txt"
                ),
            )
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "squash_conflict"
        assert "Merge conflicts detected while squashing commits" in result.message
        stderr = result.details["stderr"]
        assert isinstance(stderr, str)
        assert "CONFLICT" in stderr

    def test_pre_analysis_squash_conflict_preserves_output(self) -> None:
        """Test that conflict errors include stdout/stderr for debugging."""
        test_stdout = "Some output"
        test_stderr = "CONFLICT (content): Merge conflict in README.md"

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(2)
            .with_squash_failure(stdout=test_stdout, stderr=test_stderr)
        )

        result = execute_pre_analysis(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "squash_conflict"
        assert result.details["stdout"] == test_stdout
        assert result.details["stderr"] == test_stderr
        assert result.details["branch_name"] == "feature-branch"

    def test_pre_analysis_detects_pr_conflicts_from_github(self) -> None:
        """Test that PR conflicts are detected before any work is done."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
            .with_pr_conflicts(123)
        )

        result = execute_pre_analysis(ops)

        # Assert: Should return error, no commits made
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "pr_has_conflicts"
        assert "conflicts" in result.message.lower()
        assert result.details["pr_number"] == "123"
        assert result.details["parent_branch"] == "master"
        assert result.details["detection_method"] == "github_api"

    def test_pre_analysis_proceeds_when_no_conflicts(self) -> None:
        """Test that workflow proceeds normally when no conflicts exist."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        result = execute_pre_analysis(ops)

        # Assert: Should succeed (PR is MERGEABLE by default)
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True

    def test_pre_analysis_fallback_to_git_merge_tree(self) -> None:
        """Test fallback to git merge-tree when no PR exists."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="master").with_commits(1)
        # Configure fake to simulate conflict
        ops.git().simulate_conflict("master", "feature-branch")

        # No PR configured - should fallback to git merge-tree
        result = execute_pre_analysis(ops)

        # Assert: Should detect conflict via git merge-tree
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "pr_has_conflicts"
        assert result.details["detection_method"] == "git_merge_tree"

    def test_pre_analysis_proceeds_on_unknown_mergeability(self) -> None:
        """Test that UNKNOWN mergeability doesn't block workflow."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="master")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
            .with_pr_mergeability(123, "UNKNOWN", "UNKNOWN")
        )

        result = execute_pre_analysis(ops)

        # Assert: Should proceed with warning
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True


class TestPostAnalysisExecution:
    """Tests for post-analysis phase execution logic."""

    @patch("erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.time.sleep")
    def test_post_analysis_creates_pr(self, mock_sleep: Mock) -> None:
        """Test successfully creating new PR."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)
        # No PR initially (will be created)

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature-branch"
        # PR created but number not retrieved in this flow
        assert "PR created (number pending)" in result.message
        # Verify sleep was called 4 times (5 attempts, no sleep after last)
        assert mock_sleep.call_count == 4

    def test_post_analysis_updates_existing_pr(self) -> None:
        """Test successfully updating existing PR metadata."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_url == "https://github.com/repo/pull/123"
        assert "Updated PR #123" in result.message

    def test_post_analysis_amend_fails(self) -> None:
        """Test error when git commit --amend fails."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # No commits, so amend will fail

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "amend_failed"
        assert "Failed to amend commit" in result.message

    def test_post_analysis_submit_fails_generic(self) -> None:
        """Test error on generic submit failure."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(stdout="", stderr="generic error")
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_failed"
        assert "Failed to submit branch" in result.message

    def test_post_analysis_submit_fails_merged_parent(self) -> None:
        """Test error when parent branches merged but not in main trunk."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(
                stdout="",
                stderr="merged but the merged commits are not contained in the main trunk",
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_merged_parent"
        assert "Parent branches have been merged" in result.message

    def test_post_analysis_detects_submit_conflict(self) -> None:
        """Test that submit conflicts are detected and reported correctly."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(
                stdout="",
                stderr=(
                    "error: could not rebase\nCONFLICT (content): Merge conflict in src/main.py"
                ),
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_conflict"
        assert "Merge conflicts detected during branch submission" in result.message
        stderr = result.details["stderr"]
        assert isinstance(stderr, str)
        assert "CONFLICT" in stderr

    def test_post_analysis_conflict_check_is_first(self) -> None:
        """Test that conflict detection happens before other error patterns."""
        # This tests that even if output contains other error patterns,
        # conflicts are detected first
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(
                stdout="Branch updated remotely",  # Would normally trigger submit_diverged
                stderr="merge conflict in file.txt",  # But conflict should be detected first
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.error_type == "submit_conflict"  # Not submit_diverged
        assert "Merge conflicts detected" in result.message

    def test_post_analysis_restack_fails_with_conflict(self) -> None:
        """Test that restack phase detects conflicts before submit phase."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr="error: merge conflict in src/main.py",
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_conflict"
        assert "Merge conflicts detected during stack rebase" in result.message
        stderr = result.details["stderr"]
        assert isinstance(stderr, str)
        assert "conflict" in stderr.lower()

    def test_post_analysis_restack_fails_generic(self) -> None:
        """Test generic restack failure (not conflict-related)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr="error: failed to restack for unknown reason",
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_failed"
        assert "Failed to restack branch" in result.message

    def test_post_analysis_submit_fails_diverged(self) -> None:
        """Test error when branch has diverged from remote."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(
                stdout="branch updated remotely, must sync",
                stderr="",
            )
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_diverged"
        assert "Branch has diverged from remote" in result.message

    def test_post_analysis_submit_empty_parent(self) -> None:
        """Test error when parent branch is empty (already merged)."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_success_but_nothing_submitted()
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "submit_empty_parent"
        assert "empty parent branch" in result.message.lower()
        assert "gt track" in result.message

    def test_post_analysis_pr_update_fails(self) -> None:
        """Test warning when gh pr edit fails (PR created with metadata, update optional)."""
        # Setup: branch with PR and PR update configured to fail
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123)
            .with_pr_update_failure()  # Configure PR update to fail
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        # PR update failure is now treated as a warning, not an error
        # Metadata is already in the PR from commit, update is just to replace placeholder
        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        assert result.pr_number == 123
        assert "checkout command shows placeholder" in result.message

    @patch("erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.time.sleep")
    def test_post_analysis_pr_info_delayed(self, mock_sleep: Mock) -> None:
        """Test that PR metadata update succeeds even when PR info is delayed."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123)
            .with_pr_delay(attempts_until_visible=2)  # PR appears on 3rd attempt
        )

        result = execute_post_analysis(
            commit_message="Add feature\n\nFull description",
            ops=ops,
        )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        assert result.pr_number == 123
        assert "Updated PR #123" in result.message
        # Verify sleep was called with expected delays
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(0.5)
        mock_sleep.assert_any_call(1.0)

    def test_post_analysis_commit_includes_metadata(self, tmp_path: Path) -> None:
        """Test that commit message includes metadata in initial amend (before gt submit)."""
        # Create .impl/issue.json in temp directory
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
            encoding="utf-8",
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True

        # CRITICAL: Verify that amend_commit was called with metadata-inclusive message
        git_state = ops.git().get_state()
        assert len(git_state.commits) == 1
        commit_message = git_state.commits[0]

        # Commit message should contain metadata (but NOT erk-queue message without run_info)
        assert "This PR was generated by an agent in the `erk` queue." not in commit_message
        assert "- **Plan:** [#123](https://github.com/repo/issues/123)" in commit_message
        assert "__PLACEHOLDER_PR_NUMBER__" in commit_message  # Placeholder initially
        assert "Closes #123" in commit_message
        assert "---" in commit_message
        # And it should also contain the AI body
        assert "Full description" in commit_message

    def test_post_analysis_with_issue_reference(self, tmp_path: Path) -> None:
        """Test that PR body includes metadata section when issue.json exists."""
        # Create .impl/issue.json in temp directory
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify metadata section structure (no erk-queue message without run_info)
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        pr_body = github_state.pr_bodies[456]
        # Check metadata section components
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        assert "- **Plan:** [#123](https://github.com/repo/issues/123)" in pr_body
        assert "erk pr checkout 456" in pr_body
        assert "Closes #123" in pr_body
        assert "---" in pr_body
        assert "Full description" in pr_body

    def test_post_analysis_without_issue_reference(self, tmp_path: Path) -> None:
        """Test that PR body has no metadata section when no .impl/ metadata exists."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return temp directory without .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify that PR body has no metadata section (no agent-generated PR markers)
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        pr_body = github_state.pr_bodies[456]
        # No metadata section when no .impl/ metadata exists
        assert "This PR was generated by an agent" not in pr_body
        assert "Closes #" not in pr_body
        # Body should just be the AI-generated content
        assert pr_body == "Full description"

    def test_post_analysis_with_issue_reference_empty_body(self, tmp_path: Path) -> None:
        """Test that PR body has metadata section when commit message has only title."""
        # Create .impl/issue.json in temp directory
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 789, "issue_url": "https://github.com/repo/issues/789", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            # Commit message with only title (no body)
            result = execute_post_analysis(
                commit_message="Add feature",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify metadata section structure (empty AI body, no erk-queue without run_info)
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        pr_body = github_state.pr_bodies[456]
        # Check metadata section components
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        assert "- **Plan:** [#789](https://github.com/repo/issues/789)" in pr_body
        assert "erk pr checkout 456" in pr_body
        assert "Closes #789" in pr_body
        assert "---" in pr_body

    def test_post_analysis_with_plan_author(self, tmp_path: Path) -> None:
        """Test that PR body includes plan author in metadata when plan.md has created_by."""
        # Create .impl/plan.md with plan-header metadata block
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_md = impl_dir / "plan.md"
        plan_md.write_text(
            """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: plan-author-user
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

1. Step one
""",
            encoding="utf-8",
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify metadata section includes plan author (no erk-queue message without run_info)
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        pr_body = github_state.pr_bodies[456]
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        assert "- **Plan Author:** @plan-author-user" in pr_body
        assert "Full description" in pr_body

    def test_post_analysis_with_issue_and_plan_author(self, tmp_path: Path) -> None:
        """Test that PR body includes both issue reference and plan author in metadata."""
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        # Create .impl/plan.md with plan-header metadata block
        plan_md = impl_dir / "plan.md"
        plan_md.write_text(
            """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: combined-author
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

1. Step one
""",
            encoding="utf-8",
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        github_ops = ops.github()
        github_state = github_ops.get_state()
        # Verify metadata section includes both issue and author (no erk-queue w/o run_info)
        pr_body = github_state.pr_bodies[456]
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        assert "- **Plan:** [#123](https://github.com/repo/issues/123)" in pr_body
        assert "- **Plan Author:** @combined-author" in pr_body
        assert "Closes #123" in pr_body
        assert "Full description" in pr_body
        # Metadata should come before AI-generated content
        assert pr_body.index("---") < pr_body.index("Full description")

    def test_post_analysis_with_github_actions_run_link(self, tmp_path: Path) -> None:
        """Test that PR body includes GitHub Action link in metadata when in CI.

        When GITHUB_ACTIONS=true and run-info.json exists, the queue preamble
        and GitHub Action link should appear in the PR body.
        """
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/dagster-io/erk/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        # Create .impl/run-info.json with run URL
        run_info_json = impl_dir / "run-info.json"
        run_info_json.write_text(
            '{"run_id": "12345678901", '
            '"run_url": "https://github.com/dagster-io/erk/actions/runs/12345678901"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() and in_github_actions() for CI environment
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        in_ci_path = (
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.in_github_actions"
        )
        with (
            patch(patch_path) as mock_cwd,
            patch(in_ci_path, return_value=True),
        ):
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        github_ops = ops.github()
        github_state = github_ops.get_state()
        pr_body = github_state.pr_bodies[456]
        # Should include run link in metadata section (only in CI)
        assert "This PR was generated by an agent in the `erk` queue." in pr_body
        assert (
            "- **GitHub Action:** [View Run]"
            "(https://github.com/dagster-io/erk/actions/runs/12345678901)" in pr_body
        )

    def test_post_analysis_no_run_link_when_no_run_info(self, tmp_path: Path) -> None:
        """Test that PR body has no GitHub Action link when run-info.json is missing."""
        # Create .impl/issue.json only (no run-info.json)
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/dagster-io/erk/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return our temp directory
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        github_ops = ops.github()
        github_state = github_ops.get_state()
        pr_body = github_state.pr_bodies[456]
        # Should NOT include GitHub Action link when run-info.json is missing
        assert "GitHub Action" not in pr_body
        # Should NOT have erk-queue message without run_info
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        # But should still have other metadata
        assert "- **Plan:** [#123]" in pr_body

    def test_post_analysis_run_link_works_without_issue_reference(self, tmp_path: Path) -> None:
        """Test that PR body includes GitHub Action link in CI even without issue reference."""
        # Create .impl/run-info.json with run URL (no issue.json)
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        run_info_json = impl_dir / "run-info.json"
        run_info_json.write_text(
            '{"run_id": "12345678901", '
            '"run_url": "https://github.com/dagster-io/erk/actions/runs/12345678901"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() and in_github_actions() for CI environment
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        in_ci_path = (
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.in_github_actions"
        )
        with (
            patch(patch_path) as mock_cwd,
            patch(in_ci_path, return_value=True),
        ):
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        github_ops = ops.github()
        github_state = github_ops.get_state()
        pr_body = github_state.pr_bodies[456]
        # Should include GitHub Action link (run_url from run-info.json) when in CI
        assert "This PR was generated by an agent in the `erk` queue." in pr_body
        assert (
            "- **GitHub Action:** [View Run]"
            "(https://github.com/dagster-io/erk/actions/runs/12345678901)" in pr_body
        )
        # Should NOT have Plan link (no issue.json) or Closes line
        assert "- **Plan:**" not in pr_body
        assert "Closes #" not in pr_body

    def test_post_analysis_local_with_run_info_no_queue_preamble(self, tmp_path: Path) -> None:
        """Test that local submissions with run-info.json don't get queue preamble.

        When in_github_actions() returns False (local submission), even if run-info.json exists
        (from checking out a queue-originated PR), the queue preamble and GitHub Action
        link should NOT appear.
        """
        # Create .impl/issue.json
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/dagster-io/erk/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        # Create .impl/run-info.json (simulating checkout of queue-originated branch)
        run_info_json = impl_dir / "run-info.json"
        run_info_json.write_text(
            '{"run_id": "12345678901", '
            '"run_url": "https://github.com/dagster-io/erk/actions/runs/12345678901"}'
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() and in_github_actions() for local submission
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        in_ci_path = (
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.in_github_actions"
        )
        with (
            patch(patch_path) as mock_cwd,
            patch(in_ci_path, return_value=False),
        ):
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        github_ops = ops.github()
        github_state = github_ops.get_state()
        pr_body = github_state.pr_bodies[456]
        # Queue preamble and GitHub Action link should NOT appear when not in CI
        assert "This PR was generated by an agent in the `erk` queue." not in pr_body
        assert "- **GitHub Action:**" not in pr_body
        # But other metadata should still appear
        assert "- **Plan:** [#123]" in pr_body
        assert "Closes #123" in pr_body
        assert "Full description" in pr_body


class TestOrchestrateWorkflow:
    """Tests for orchestrate_submit_workflow function."""

    @pytest.mark.skip(reason="Requires Claude CLI mock - needs validation refactor")
    def test_orchestrate_success(self) -> None:
        """Test successful orchestration through all phases."""
        from unittest.mock import patch

        # Setup fake to succeed at each step
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Mock the agent invocation to return a commit message
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._invoke_commit_message_agent"
        ) as mock_agent:
            mock_agent.return_value = "Add feature\n\nDetailed description of the feature"

            result = orchestrate_submit_workflow(ops)

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_url == "https://github.com/repo/pull/123"

    def test_orchestrate_pre_analysis_error(self) -> None:
        """Test error in pre-analysis phase."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_gt_unauthenticated()
        )

        result = orchestrate_submit_workflow(ops)

        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "gt_not_authenticated"

    def test_orchestrate_diff_extraction_error(self) -> None:
        """Test error getting diff."""
        from dataclasses import replace

        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)
        # Remove parent branch to simulate get_diff_context failure
        gt_state = ops.graphite().get_state()
        ops.graphite()._state = replace(gt_state, branch_parents={})

        result = orchestrate_submit_workflow(ops)

        # Pre-analysis catches the no_parent error before we get to diff extraction
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "no_parent"
        assert "Could not determine parent branch" in result.message

    @pytest.mark.skip(reason="Requires Claude CLI mock - needs validation refactor")
    def test_orchestrate_agent_invocation_error_fails_hard(self) -> None:
        """Test that AI failure causes hard failure (no fallback).

        The workflow now requires Claude to be available and working.
        If AI generation fails, the entire workflow fails.
        """
        from unittest.mock import patch

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Mock agent invocation to raise RuntimeError
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._invoke_commit_message_agent"
        ) as mock_agent:
            mock_agent.side_effect = RuntimeError("Agent execution failed")

            result = orchestrate_submit_workflow(ops)

        # AI failure now causes hard failure
        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "ai_generation_failed"
        assert "AI generation failed" in result.message

    @pytest.mark.skip(reason="Requires Claude CLI mock - needs validation refactor")
    def test_orchestrate_fails_hard_when_ai_fails(self) -> None:
        """Test that workflow fails when AI generation fails (no fallback).

        The workflow now requires Claude AI to work. If AI generation fails,
        the entire workflow returns an error instead of continuing with fallback.
        """
        from unittest.mock import patch

        ops = (
            FakeGtKitOps()
            .with_branch("fix-workflow-temp-file", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Mock agent invocation to raise RuntimeError
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._invoke_commit_message_agent"
        ) as mock_agent:
            mock_agent.side_effect = RuntimeError("Agent execution failed")

            result = orchestrate_submit_workflow(ops)

        # Workflow fails instead of continuing with fallback
        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "ai_generation_failed"

        # Verify PR metadata was NOT updated since workflow failed
        github_state = ops.github().get_state()
        # PR 123 should NOT have been updated
        assert 123 not in github_state.pr_titles


class TestSubmitBranchCLI:
    """Tests for submit_branch CLI commands."""

    def test_pre_analysis_command_success(self, runner: CliRunner) -> None:
        """Test pre-analysis CLI command with successful execution."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        # Monkey patch execute_pre_analysis to use our fake ops
        import erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch as submit_module

        original_execute = submit_module.execute_pre_analysis

        def patched_execute(ops_param: object | None = None) -> object:
            return original_execute(ops)

        submit_module.execute_pre_analysis = patched_execute

        try:
            result = runner.invoke(pr_submit, ["pre-analysis"])

            assert result.exit_code == 0
            output = extract_json_from_output(result.output)
            assert output["success"] is True
            assert output["branch_name"] == "feature-branch"
            assert output["commit_count"] == 1
        finally:
            submit_module.execute_pre_analysis = original_execute

    def test_post_analysis_command_success(self, runner: CliRunner) -> None:
        """Test post-analysis CLI command with successful execution."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Monkey patch execute_post_analysis to use our fake ops
        import erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch as submit_module

        original_execute = submit_module.execute_post_analysis

        def patched_execute(commit_message: str, ops_param: object | None = None) -> object:
            return original_execute(commit_message, ops)

        submit_module.execute_post_analysis = patched_execute

        try:
            result = runner.invoke(
                pr_submit,
                [
                    "post-analysis",
                    "--commit-message",
                    "Add feature\n\nDescription",
                ],
            )

            assert result.exit_code == 0
            output = extract_json_from_output(result.output)
            assert output["success"] is True
            assert output["pr_number"] == 123
        finally:
            submit_module.execute_post_analysis = original_execute


class TestValidateClaudeAvailability:
    """Tests for _validate_claude_availability() function."""

    def test_claude_not_in_path(self) -> None:
        """Test when Claude CLI is not in PATH."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            _validate_claude_availability,
        )

        with patch("shutil.which", return_value=None):
            available, error_msg = _validate_claude_availability()
            assert available is False
            assert "Claude CLI not found in PATH" in error_msg
            assert "https://claude.ai/download" in error_msg

    def test_claude_not_executable(self) -> None:
        """Test when Claude CLI exists but is not executable."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            _validate_claude_availability,
        )

        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("os.access", return_value=False):
                available, error_msg = _validate_claude_availability()
                assert available is False
                assert "not executable" in error_msg
                assert "/usr/local/bin/claude" in error_msg

    def test_claude_available(self) -> None:
        """Test when Claude CLI is available and executable."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            _validate_claude_availability,
        )

        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("os.access", return_value=True):
                available, error_msg = _validate_claude_availability()
                assert available is True
                assert error_msg == ""


class TestInvokeCommitMessageAgentTempFile:
    """Tests for _invoke_commit_message_agent() with temp file approach."""

    def test_creates_temp_file_with_diff(self, tmp_path: Path) -> None:
        """Test that agent creates temporary file with diff content."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="diff --git a/test.py b/test.py\n+new line",
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            f"Test commit message\n\nTest description\n\n{ERK_COMMIT_MESSAGE_MARKER}"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _invoke_commit_message_agent(diff_context)

            # Verify subprocess was called with agent
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "claude" in call_args
            assert "--agents" in call_args
            assert "commit-message-generator" in call_args

            # Verify result (marker is stripped)
            assert result == "Test commit message\n\nTest description"

    def test_cleans_up_temp_file_on_success(self, tmp_path: Path) -> None:
        """Test that temp file is cleaned up after successful invocation."""
        import tempfile

        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = f"Add feature for testing cleanup\n\n{ERK_COMMIT_MESSAGE_MARKER}"
        mock_result.stderr = ""

        temp_files_created = []
        original_tempfile = tempfile.NamedTemporaryFile

        def mock_tempfile(*args, **kwargs):
            f = original_tempfile(*args, **kwargs)
            temp_files_created.append(f.name)
            return f

        with patch("subprocess.run", return_value=mock_result):
            with patch("tempfile.NamedTemporaryFile", side_effect=mock_tempfile):
                _invoke_commit_message_agent(diff_context)

        # Verify temp file was cleaned up
        for temp_file in temp_files_created:
            assert not Path(temp_file).exists()

    def test_cleans_up_temp_file_on_error(self, tmp_path: Path) -> None:
        """Test that temp file is cleaned up even when agent fails."""
        import tempfile

        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Agent failed"

        temp_files_created = []
        original_tempfile = tempfile.NamedTemporaryFile

        def mock_tempfile(*args, **kwargs):
            f = original_tempfile(*args, **kwargs)
            temp_files_created.append(f.name)
            return f

        with patch("subprocess.run", return_value=mock_result):
            with patch("tempfile.NamedTemporaryFile", side_effect=mock_tempfile):
                try:
                    _invoke_commit_message_agent(diff_context)
                except RuntimeError:
                    pass  # Expected

        # Verify temp file was cleaned up
        for temp_file in temp_files_created:
            assert not Path(temp_file).exists()

    def test_raises_runtime_error_on_non_zero_exit(self, tmp_path: Path) -> None:
        """Test that RuntimeError is raised when agent returns non-zero exit code."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Claude agent failed"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Agent failed"):
                _invoke_commit_message_agent(diff_context)

    def test_raises_runtime_error_on_empty_output(self, tmp_path: Path) -> None:
        """Test that RuntimeError is raised when agent returns no output."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Agent returned no output"):
                _invoke_commit_message_agent(diff_context)

    def test_raises_runtime_error_on_invalid_commit_message(self, tmp_path: Path) -> None:
        """Test that RuntimeError is raised when agent returns invalid commit message.

        This catches the case where Claude returns a permission request instead of
        a commit message (the bug that caused PR #1478).
        """
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        # Simulate Claude asking for permission instead of generating commit message
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "I need permission to read that file. Could you either:\n"
            "1. Grant me permission to read files from `/tmp/`\n"
            "2. Or share the diff content directly?"
        )
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="did not return a valid commit message"):
                _invoke_commit_message_agent(diff_context)

    def test_raises_runtime_error_on_question_first_line(self, tmp_path: Path) -> None:
        """Test that RuntimeError is raised when first line is a question."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            DiffContextResult,
            _invoke_commit_message_agent,
        )

        diff_context = DiffContextResult(
            success=True,
            repo_root=str(tmp_path),
            current_branch="feature",
            parent_branch="main",
            diff="test diff",
        )

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Could you grant me permission to read /tmp/file.diff?"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="did not return a valid commit message"):
                _invoke_commit_message_agent(diff_context)


class TestOrchestrateWorkflowClaudeValidation:
    """Tests for orchestrate_submit_workflow with Claude validation."""

    @patch("erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.time.sleep")
    def test_fails_when_claude_not_available(self, mock_sleep: Mock) -> None:
        """Test that workflow fails when Claude CLI is not available."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            PostAnalysisError,
            orchestrate_submit_workflow,
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        # Mock Claude validation to fail
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._validate_claude_availability",
            return_value=(False, "Claude CLI not found"),
        ):
            result = orchestrate_submit_workflow(ops)

        # Assert: Should return error instead of continuing
        assert isinstance(result, PostAnalysisError)
        assert result.error_type == "claude_not_available"
        assert "Claude CLI is not available" in result.message

    @patch("erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.time.sleep")
    def test_fails_when_ai_generation_fails(self, mock_sleep: Mock) -> None:
        """Test that workflow fails when AI generation raises exception."""
        from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
            PostAnalysisError,
            orchestrate_submit_workflow,
        )

        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/org/repo/pull/123")
        )

        # Mock Claude validation to succeed
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._validate_claude_availability",
            return_value=(True, ""),
        ):
            # Mock agent invocation to fail
            with patch(
                "erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch._invoke_commit_message_agent",
                side_effect=RuntimeError("Agent crashed"),
            ):
                result = orchestrate_submit_workflow(ops)

        # Assert: Should return error instead of continuing
        assert isinstance(result, PostAnalysisError)
        assert result.error_type == "ai_generation_failed"
        assert "AI generation failed" in result.message
