"""Tests for submit_branch kit CLI command using fake ops."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from erk.data.kits.gt.kit_cli_commands.gt.submit_branch import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
    execute_post_analysis,
    execute_pre_analysis,
    submit_squashed_branch,
)
from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestPreAnalysisExecution:
    """Tests for pre-analysis phase execution logic."""

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
        ops = FakeGtKitOps().with_branch("feature-branch", parent="master").with_commits(1)

        # Mock GitHub to return CONFLICTING status
        with patch("erk.core.github.real.RealGitHub") as mock_github_class:
            mock_github = mock_github_class.return_value
            mock_pr_info = Mock()
            mock_pr_info.pr_number = 123
            mock_pr_info.url = "https://github.com/org/repo/pull/123"
            mock_github.get_pr_status.return_value = mock_pr_info

            mock_mergeability = Mock()
            mock_mergeability.mergeable = "CONFLICTING"
            mock_mergeability.merge_state_status = "DIRTY"
            mock_github.get_pr_mergeability.return_value = mock_mergeability

            result = execute_pre_analysis(ops)

        # Assert: Should return error, no commits made
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "pr_has_conflicts"
        assert "conflicts" in result.message.lower()
        assert result.details["pr_number"] == "123"
        assert result.details["parent_branch"] == "master"

    def test_pre_analysis_proceeds_when_no_conflicts(self) -> None:
        """Test that workflow proceeds normally when no conflicts exist."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="master").with_commits(1)

        # Mock GitHub to return MERGEABLE status
        with patch("erk.core.github.real.RealGitHub") as mock_github_class:
            mock_github = mock_github_class.return_value
            mock_pr_info = Mock()
            mock_pr_info.pr_number = 123
            mock_pr_info.url = "https://github.com/org/repo/pull/123"
            mock_github.get_pr_status.return_value = mock_pr_info

            mock_mergeability = Mock()
            mock_mergeability.mergeable = "MERGEABLE"
            mock_mergeability.merge_state_status = "CLEAN"
            mock_github.get_pr_mergeability.return_value = mock_mergeability

            result = execute_pre_analysis(ops)

        # Assert: Should succeed
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True

    def test_pre_analysis_fallback_to_git_merge_tree(self) -> None:
        """Test fallback to git merge-tree when no PR exists."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="master").with_commits(1)
        # Configure fake to simulate conflict
        ops.git().simulate_conflict("master", "feature-branch")

        # Mock GitHub to return no PR
        with patch("erk.core.github.real.RealGitHub") as mock_github_class:
            mock_github = mock_github_class.return_value
            mock_pr_info = Mock()
            mock_pr_info.pr_number = None
            mock_pr_info.url = None
            mock_github.get_pr_status.return_value = mock_pr_info

            result = execute_pre_analysis(ops)

        # Assert: Should detect conflict via git merge-tree
        assert isinstance(result, PreAnalysisError)
        assert result.error_type == "pr_has_conflicts"
        assert result.details["detection_method"] == "git_merge_tree"

    def test_pre_analysis_proceeds_on_unknown_mergeability(self) -> None:
        """Test that UNKNOWN mergeability doesn't block workflow."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="master").with_commits(1)

        # Mock GitHub to return UNKNOWN status
        with patch("erk.core.github.real.RealGitHub") as mock_github_class:
            mock_github = mock_github_class.return_value
            mock_pr_info = Mock()
            mock_pr_info.pr_number = 123
            mock_pr_info.url = "https://github.com/org/repo/pull/123"
            mock_github.get_pr_status.return_value = mock_pr_info

            mock_mergeability = Mock()
            mock_mergeability.mergeable = "UNKNOWN"
            mock_mergeability.merge_state_status = "UNKNOWN"
            mock_github.get_pr_mergeability.return_value = mock_mergeability

            result = execute_pre_analysis(ops)

        # Assert: Should proceed with warning
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True


class TestPostAnalysisExecution:
    """Tests for post-analysis phase execution logic."""

    @patch("erk.data.kits.gt.kit_cli_commands.gt.submit_branch.time.sleep")
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

    def test_post_analysis_pr_update_fails(self) -> None:
        """Test error when gh pr edit fails."""
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

        assert isinstance(result, PostAnalysisError)
        assert result.success is False
        assert result.error_type == "pr_update_failed"
        assert "failed to update PR #123 metadata" in result.message

    @patch("erk.data.kits.gt.kit_cli_commands.gt.submit_branch.time.sleep")
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

    def test_post_analysis_with_issue_reference(self, tmp_path: Path) -> None:
        """Test that PR body includes 'Closes #N' when issue.json exists."""
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
        patch_path = "erk.data.kits.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify that update_pr_metadata was called with "Closes #123" prepended
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        assert github_state.pr_bodies[456] == "Closes #123\n\nFull description"

    def test_post_analysis_without_issue_reference(self, tmp_path: Path) -> None:
        """Test that PR body is unchanged when issue.json does not exist."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )

        # Mock Path.cwd() to return temp directory without .impl/issue.json
        patch_path = "erk.data.kits.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = execute_post_analysis(
                commit_message="Add feature\n\nFull description",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify that PR body is unchanged (no "Closes #N")
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        assert github_state.pr_bodies[456] == "Full description"

    def test_post_analysis_with_issue_reference_empty_body(self, tmp_path: Path) -> None:
        """Test that PR body is just 'Closes #N' when commit message has only title."""
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
        patch_path = "erk.data.kits.gt.kit_cli_commands.gt.submit_branch.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path

            # Commit message with only title (no body)
            result = execute_post_analysis(
                commit_message="Add feature",
                ops=ops,
            )

        assert isinstance(result, PostAnalysisResult)
        assert result.success is True
        # Verify that PR body is just "Closes #789\n\n" (no extra content)
        github_ops = ops.github()
        github_state = github_ops.get_state()
        assert github_state.pr_titles[456] == "Add feature"
        assert github_state.pr_bodies[456] == "Closes #789\n\n"


class TestSubmitBranchCLI:
    """Tests for submit_branch CLI commands."""

    def test_pre_analysis_command_success(self, runner: CliRunner) -> None:
        """Test pre-analysis CLI command with successful execution."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        # Monkey patch execute_pre_analysis to use our fake ops
        import erk.data.kits.gt.kit_cli_commands.gt.submit_branch as submit_module

        original_execute = submit_module.execute_pre_analysis

        def patched_execute(ops_param: object | None = None) -> object:
            return original_execute(ops)

        submit_module.execute_pre_analysis = patched_execute

        try:
            result = runner.invoke(submit_squashed_branch, ["pre-analysis"])

            assert result.exit_code == 0
            output = json.loads(result.output)
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
        import erk.data.kits.gt.kit_cli_commands.gt.submit_branch as submit_module

        original_execute = submit_module.execute_post_analysis

        def patched_execute(commit_message: str, ops_param: object | None = None) -> object:
            return original_execute(commit_message, ops)

        submit_module.execute_post_analysis = patched_execute

        try:
            result = runner.invoke(
                submit_squashed_branch,
                [
                    "post-analysis",
                    "--commit-message",
                    "Add feature\n\nDescription",
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["success"] is True
            assert output["pr_number"] == 123
        finally:
            submit_module.execute_post_analysis = original_execute
