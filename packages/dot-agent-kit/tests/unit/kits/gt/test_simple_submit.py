"""Tests for simple_submit kit CLI command using fake ops."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit import (
    complete_submission,
    execute_simple_submit,
    simple_submit,
)
from erk_shared.integrations.time.fake import FakeTime

from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestExecuteSimpleSubmit:
    """Tests for execute_simple_submit() function (prepare phase)."""

    def test_prepare_with_no_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test prepare phase when no uncommitted changes exist."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        # Mock Path.cwd() to return temp directory without .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)

        assert result["success"] is True
        assert result["branch"] == "feature-branch"
        assert result["parent"] == "main"
        assert "diff" in result
        assert result["issue_number"] is None

    def test_prepare_with_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test prepare phase commits uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
            .with_commits(0)
        )

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(description="WIP changes", ops=ops)

        assert result["success"] is True
        # Verify commit was created
        assert ops.git().count_commits_in_branch("main") == 1

    def test_prepare_with_uncommitted_changes_default_message(self, tmp_path: Path) -> None:
        """Test prepare phase uses default commit message when description not provided."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
            .with_commits(0)
        )

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)  # No description provided

        assert result["success"] is True
        # Check default message was used
        assert ops.git().get_state().commits[0] == "WIP: Prepare for submission"

    def test_prepare_fails_when_add_fails(self, tmp_path: Path) -> None:
        """Test error when git add fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
            .with_add_failure()  # Configure add to fail
        )

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)

        assert result["success"] is False
        assert result["error"] == "Failed to stage changes"

    def test_prepare_fails_when_restack_fails(self, tmp_path: Path) -> None:
        """Test error when restack fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure()
        )

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)

        assert result["success"] is False
        assert result["error"] == "Failed to restack branch"

    def test_prepare_fails_when_no_branch(self, tmp_path: Path) -> None:
        """Test error when current branch cannot be determined."""
        ops = FakeGtKitOps()
        # Set current_branch to empty to simulate failure
        from dataclasses import replace

        ops.git()._state = replace(ops.git().get_state(), current_branch="")

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)

        assert result["success"] is False
        assert result["error"] == "Could not determine current branch"

    def test_prepare_fails_when_no_parent(self, tmp_path: Path) -> None:
        """Test error when parent branch cannot be determined."""
        ops = FakeGtKitOps().with_branch("orphan-branch", parent="main")
        # Remove parent relationship to simulate gt parent failure
        from dataclasses import replace

        gt_state = ops.graphite().get_state()
        ops.graphite()._state = replace(gt_state, branch_parents={})

        # Mock Path.cwd() to avoid picking up real .impl/issue.json
        patch_path = "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.Path.cwd"
        with patch(patch_path) as mock_cwd:
            mock_cwd.return_value = tmp_path
            result = execute_simple_submit(ops=ops)

        assert result["success"] is False
        assert result["error"] == "Could not determine parent branch"

    def test_prepare_with_issue_reference(self, tmp_path: Path) -> None:
        """Test prepare phase includes issue_number when .impl/issue.json exists."""
        # Create .impl/issue.json in temp directory
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/repo/issues/123", '
            '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}'
        )

        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        result = execute_simple_submit(ops=ops, impl_dir=impl_dir)

        assert result["success"] is True
        assert result["issue_number"] == 123

    def test_prepare_without_issue_reference(self, tmp_path: Path) -> None:
        """Test prepare phase returns None for issue_number when no .impl/issue.json."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        result = execute_simple_submit(ops=ops, impl_dir=tmp_path / ".impl")

        assert result["success"] is True
        assert result["issue_number"] is None


class TestCompleteSubmission:
    """Tests for complete_submission() function (complete phase)."""

    def test_complete_amends_commit_and_submits(self) -> None:
        """Test complete phase amends commit and submits PR."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )
        result = complete_submission("Add feature\n\nFull description", ops=ops)

        assert result["success"] is True
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/repo/pull/123"

    def test_complete_with_single_commit_no_squash(self) -> None:
        """Test complete phase with single commit doesn't squash."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1).with_pr(123)
        )
        result = complete_submission("Add feature", squash=True, ops=ops)

        assert result["success"] is True
        # No squash should have been attempted (count == 1)

    def test_complete_with_multiple_commits_squashes(self) -> None:
        """Test complete phase with multiple commits performs squash."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)  # Multiple commits
            .with_pr(123)
        )
        result = complete_submission("Add feature", squash=True, ops=ops)

        assert result["success"] is True

    def test_complete_with_squash_disabled(self) -> None:
        """Test complete phase respects squash=False flag."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(3).with_pr(123)
        )
        result = complete_submission("Add feature", squash=False, ops=ops)

        assert result["success"] is True
        # Squash should have been skipped

    def test_complete_fails_when_amend_fails(self) -> None:
        """Test error when git commit --amend fails."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # No commits, so amend will fail
        result = complete_submission("Add feature", ops=ops)

        assert result["success"] is False
        assert result["error"] == "Failed to amend commit"

    def test_complete_fails_when_squash_fails(self) -> None:
        """Test error when gt squash fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(3)
            .with_squash_failure(stderr="Squash conflict")
        )
        result = complete_submission("Add feature", squash=True, ops=ops)

        assert result["success"] is False
        assert "Failed to squash" in result["error"]
        assert "Squash conflict" in result["error"]

    def test_complete_fails_when_submit_fails(self) -> None:
        """Test error when gt submit fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(stderr="Submit error")
        )
        result = complete_submission("Add feature", ops=ops)

        assert result["success"] is False
        assert result["error"] == "Submit error"

    def test_complete_succeeds_when_pr_info_unavailable(self) -> None:
        """Test success with message when PR info cannot be retrieved."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)
        # No PR configured, so get_pr_info() will return None
        result = complete_submission("Add feature", ops=ops)

        assert result["success"] is True
        assert result["pr_number"] is None
        assert result["pr_url"] is None
        assert "PR submitted but could not retrieve PR info" in result["message"]

    def test_complete_stages_uncommitted_changes_before_amend(self) -> None:
        """Test that complete phase stages uncommitted changes before amending commit.

        This ensures the working directory is clean after submission completes.
        Regression test for: uncommitted changes were left unstaged after simple-submit.
        """
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)  # Start with 1 commit
            .with_uncommitted_files(["new_file.py", "modified_file.py"])  # Add uncommitted changes
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Before complete_submission, verify we have uncommitted changes
        assert ops.git().has_uncommitted_changes() is True

        result = complete_submission("Add feature\n\nFull description", ops=ops)

        assert result["success"] is True
        # After complete_submission, working directory should be clean
        assert ops.git().has_uncommitted_changes() is False
        # The uncommitted files should now be part of the amended commit
        git_state = ops.git().get_state()
        assert "new_file.py" in git_state.tracked_files
        assert "modified_file.py" in git_state.tracked_files


class TestIssueLinkling:
    """Tests for GitHub issue linking functionality."""

    def test_complete_with_issue_number_adds_closes_to_commit(self) -> None:
        """Test that issue_number adds 'Closes #N' to commit message."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1).with_pr(456)
        )
        result = complete_submission(
            "Add feature\n\nFull description",
            issue_number=123,
            ops=ops,
        )

        assert result["success"] is True
        assert result["issue_number"] == 123
        # Verify commit message was amended with "Closes #123"
        git_state = ops.git().get_state()
        assert git_state.commits[-1] == "Add feature\n\nFull description\n\nCloses #123"

    def test_complete_with_issue_number_adds_closes_to_pr_body(self) -> None:
        """Test that issue_number adds 'Closes #N' to PR body."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(456, url="https://github.com/repo/pull/456")
        )
        result = complete_submission(
            "Add feature\n\nFull description",
            issue_number=123,
            ops=ops,
        )

        assert result["success"] is True
        # Verify PR body was updated with "Closes #123" (should appear only once)
        github_state = ops.github().get_state()
        assert github_state.pr_titles[456] == "Add feature"
        assert github_state.pr_bodies[456] == "Full description\n\nCloses #123"

    def test_complete_with_issue_number_title_only_commit(self) -> None:
        """Test that PR body is 'Closes #N' when commit message has only title."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1).with_pr(456)
        )
        result = complete_submission(
            "Add feature",  # Title only, no body
            issue_number=789,
            ops=ops,
        )

        assert result["success"] is True
        # Verify PR body is just "\n\nCloses #789"
        github_state = ops.github().get_state()
        assert github_state.pr_titles[456] == "Add feature"
        assert github_state.pr_bodies[456] == "\n\nCloses #789"

    def test_complete_without_issue_number_no_closes_added(self) -> None:
        """Test that no 'Closes #N' is added when issue_number is None."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1).with_pr(456)
        )
        result = complete_submission(
            "Add feature\n\nFull description",
            issue_number=None,
            ops=ops,
        )

        assert result["success"] is True
        # Verify commit message unchanged
        git_state = ops.git().get_state()
        assert git_state.commits[-1] == "Add feature\n\nFull description"


class TestPRInfoRetry:
    """Tests for PR info polling with exponential backoff retry."""

    def test_complete_retries_pr_info_when_initially_unavailable(self) -> None:
        """Test that PR info is retried when not immediately available after submit."""
        fake_time = FakeTime()
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
            .with_pr_delay(attempts_until_visible=2)  # PR visible on 3rd attempt (after 2 failures)
        )
        result = complete_submission("Add feature", verbose=True, ops=ops, time=fake_time)

        assert result["success"] is True
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/repo/pull/123"
        # Verify exponential backoff: 2 failed attempts with 1s, 2s delays, then success on 3rd
        assert fake_time.sleep_calls == [1, 2]

    def test_complete_succeeds_when_pr_info_never_available(self) -> None:
        """Test that complete succeeds with message when PR info never becomes available."""
        fake_time = FakeTime()
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr_delay(attempts_until_visible=999)  # PR never visible within retry window
        )
        result = complete_submission("Add feature", verbose=True, ops=ops, time=fake_time)

        assert result["success"] is True
        assert result["pr_number"] is None
        assert result["pr_url"] is None
        assert "PR submitted but could not retrieve PR info after retries" in result["message"]
        # Verify all 3 attempts with backoff: 1s, 2s (no sleep after last attempt)
        assert fake_time.sleep_calls == [1, 2]


class TestMarkPRReady:
    """Tests for mark_pr_ready() functionality (draft PR fix)."""

    def test_complete_marks_pr_as_ready(self) -> None:
        """Test that complete phase calls mark_pr_ready after PR creation."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )
        result = complete_submission("Add feature", ops=ops)

        assert result["success"] is True
        # mark_pr_ready was called (verified by fake implementation)
        # In real implementation, this would convert draft PR to ready

    def test_complete_continues_when_mark_pr_ready_fails(self) -> None:
        """Test that workflow continues even if mark_pr_ready fails."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)
        # No PR configured, so mark_pr_ready will fail (returns False)
        result = complete_submission("Add feature", ops=ops)

        # Should still succeed even though mark_pr_ready failed
        assert result["success"] is True


class TestSimpleSubmitCLI:
    """Tests for simple_submit CLI command."""

    def test_cli_prepare_success(self, runner: CliRunner) -> None:
        """Test CLI --prepare flag with successful execution."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1)

        # Monkey patch RealGtKit to use our fake ops
        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(simple_submit, ["--prepare"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["branch"] == "feature-branch"

    def test_cli_prepare_with_description(self, runner: CliRunner) -> None:
        """Test CLI --prepare with --description flag."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.py"])
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(
                simple_submit,
                ["--prepare", "--description", "WIP changes"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

    def test_cli_complete_success(self, runner: CliRunner) -> None:
        """Test CLI --complete flag with successful execution."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(
                simple_submit,
                ["--complete", "--message", "Add feature\n\nDescription"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 123

    def test_cli_complete_with_issue_number(self, runner: CliRunner) -> None:
        """Test CLI --complete with --issue-number flag."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(1).with_pr(456)
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(
                simple_submit,
                ["--complete", "--message", "Add feature", "--issue-number", "123"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["issue_number"] == 123

    def test_cli_complete_with_no_squash(self, runner: CliRunner) -> None:
        """Test CLI --complete with --no-squash flag."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_commits(3).with_pr(123)
        )

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(
                simple_submit,
                ["--complete", "--message", "Add feature", "--no-squash"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

    def test_cli_error_both_prepare_and_complete(self, runner: CliRunner) -> None:
        """Test CLI error when both --prepare and --complete are specified."""
        result = runner.invoke(simple_submit, ["--prepare", "--complete"])

        assert result.exit_code == 1
        assert "Cannot use --prepare and --complete together" in result.output

    def test_cli_error_neither_prepare_nor_complete(self, runner: CliRunner) -> None:
        """Test CLI error when neither --prepare nor --complete is specified."""
        result = runner.invoke(simple_submit, [])

        assert result.exit_code == 1
        assert "Must specify either --prepare or --complete" in result.output

    def test_cli_error_complete_without_message(self, runner: CliRunner) -> None:
        """Test CLI error when --complete is used without --message."""
        result = runner.invoke(simple_submit, ["--complete"])

        assert result.exit_code == 1
        assert "--message is required for --complete" in result.output

    def test_cli_prepare_failure_exits_with_error(self, runner: CliRunner) -> None:
        """Test CLI exits with error code when prepare fails."""
        ops = FakeGtKitOps()
        # Set current_branch to empty to trigger failure
        from dataclasses import replace

        ops.git()._state = replace(ops.git().get_state(), current_branch="")

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(simple_submit, ["--prepare"])

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False

    def test_cli_complete_failure_exits_with_error(self, runner: CliRunner) -> None:
        """Test CLI exits with error code when complete fails."""
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # No commits, so amend will fail

        with patch(
            "erk_shared.integrations.gt.kit_cli_commands.gt.simple_submit.RealGtKit"
        ) as mock_kit:
            mock_kit.return_value = ops
            result = runner.invoke(
                simple_submit,
                ["--complete", "--message", "Add feature"],
            )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
