"""Tests for update_pr kit CLI command using fake ops."""

import json

import pytest
from click.testing import CliRunner
from tests.kits.gt.fake_ops import FakeGtKit

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.update_pr import (
    UpdatePRError,
    UpdatePRResult,
    execute_update_pr,
    update_pr,
)
<<<<<<<< 88d25308bf4f8e963754dbaf39a63d9239b9119c:packages/dot-agent-kit/tests/unit/kits/gt/test_update_pr.py
from tests.unit.kits.gt.fake_ops import FakeGtKitOps
========
>>>>>>>> 7ea7fa23d6a40698c99b219ea05bae79dafb3b54:packages/dot-agent-kit/tests/kits/gt/test_update_pr.py


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestUpdatePRWorkflow:
    """Tests for update_pr workflow logic using fakes."""

    def test_success_with_uncommitted_changes(self) -> None:
        """Test successfully updating PR with uncommitted changes."""
        # Setup: branch with PR and uncommitted files
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, url="https://github.com/repo/pull/123")
            .with_uncommitted_files(["file1.py", "file2.py"])
        )

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_url == "https://github.com/repo/pull/123"
        assert result.branch_name == "feature-branch"
        assert result.had_changes is True
        assert "Committed changes" in result.message

    def test_success_without_uncommitted_changes(self) -> None:
        """Test successfully updating PR without uncommitted changes."""
        # Setup: branch with PR but no uncommitted files
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, url="https://github.com/repo/pull/123")
        )
        # No uncommitted files

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.had_changes is False
        assert "No uncommitted changes" in result.message

    def test_error_no_pr(self) -> None:
        """Test error when no PR exists for branch."""
        # Setup: branch without PR
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # Don't call with_pr(), so no PR exists

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRError)
        assert result.success is False
        assert result.error_type == "no_pr"
        assert "No PR associated with current branch" in result.message
        assert result.details["branch_name"] == "feature-branch"

    def test_error_commit_failed(self) -> None:
        """Test error when git add fails during commit."""
        # Setup: branch with PR, uncommitted files, and add configured to fail
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_uncommitted_files(["file.py"])
            .with_add_failure()  # Configure add to fail
        )

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRError)
        assert result.success is False
        assert result.error_type == "commit_failed"
        assert "Failed to stage uncommitted changes" in result.message

    def test_error_restack_failed(self) -> None:
        """Test error when restack encounters conflicts."""
        # Setup: branch with PR, restack configured to fail
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_restack_failure()
        )

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRError)
        assert result.success is False
        assert result.error_type == "restack_failed"
        assert "Conflicts occurred during restack" in result.message

    def test_error_submit_failed(self) -> None:
        """Test error when submit fails."""
        # Setup: branch with PR, submit configured to fail
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
            .with_submit_failure()
        )

        result = execute_update_pr(ops)

        assert isinstance(result, UpdatePRError)
        assert result.success is False
        assert result.error_type == "submit_failed"
        assert "Failed to submit updates" in result.message


class TestUpdatePRCLI:
    """Tests for update_pr CLI command."""

    def test_command_success(self, runner: CliRunner) -> None:
        """Test CLI command with successful update."""
        # Setup: create ops and inject into execute function via monkey patch
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Monkey patch execute_update_pr to use our fake ops
        import dot_agent_kit.data.kits.gt.kit_cli_commands.gt.update_pr as update_pr_module

        original_execute = update_pr_module.execute_update_pr

        def patched_execute(ops_param: object | None = None) -> object:
            return original_execute(ops)

        update_pr_module.execute_update_pr = patched_execute

        try:
            result = runner.invoke(update_pr)

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["success"] is True
            assert output["pr_number"] == 123
            assert output["branch_name"] == "feature-branch"
        finally:
            # Restore original function
            update_pr_module.execute_update_pr = original_execute

    def test_command_error(self, runner: CliRunner) -> None:
        """Test CLI command error output format."""
        # Setup: ops with no PR to trigger error
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")

        # Monkey patch execute_update_pr to use our fake ops
        import dot_agent_kit.data.kits.gt.kit_cli_commands.gt.update_pr as update_pr_module

        original_execute = update_pr_module.execute_update_pr

        def patched_execute(ops_param: object | None = None) -> object:
            return original_execute(ops)

        update_pr_module.execute_update_pr = patched_execute

        try:
            result = runner.invoke(update_pr)

            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
            assert output["error_type"] == "no_pr"
        finally:
            # Restore original function
            update_pr_module.execute_update_pr = original_execute
