"""Tests for update_pr kit CLI command using fake ops."""

import json

import pytest
from click.testing import CliRunner

from erk.data.kits.gt.kit_cli_commands.gt.update_pr import (
    execute_update_pr,
    update_pr,
)
from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestExecuteUpdatePr:
    """Tests for execute_update_pr function."""

    def test_update_pr_success_with_uncommitted_changes(self) -> None:
        """Test successful update with uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        # Monkey patch execute_update_pr to use our fake ops
        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is True
            assert result["pr_number"] == 123
            assert result["pr_url"] == "https://github.com/repo/pull/123"
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_success_without_uncommitted_changes(self) -> None:
        """Test successful update without uncommitted changes."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is True
            assert result["pr_number"] == 123
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_restack_fails_generic(self) -> None:
        """Test error when restack fails with generic error."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(stdout="", stderr="Failed to rebase")
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert result["error_type"] == "restack_failed"
            assert "Failed to restack branch" in result["error"]
            assert "stderr" in result["details"]
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_restack_conflict_detected_via_stderr(self) -> None:
        """Test that restack conflicts are detected via stderr pattern matching."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr=(
                    "error: could not apply abc123... commit message\n"
                    "CONFLICT (content): Merge conflict in file.txt"
                ),
            )
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert result["error_type"] == "restack_conflict"
            assert "Merge conflict detected during restack" in result["error"]
            assert "gt restack --continue" in result["error"]
            assert "CONFLICT" in result["details"]["stderr"]
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_restack_conflict_detected_via_stdout(self) -> None:
        """Test that restack conflicts are detected via stdout pattern matching."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="Merge conflict in src/main.py",
                stderr="",
            )
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert result["error_type"] == "restack_conflict"
            assert "Merge conflict detected during restack" in result["error"]
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_restack_conflict_case_insensitive(self) -> None:
        """Test that conflict detection is case insensitive."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(
                stdout="",
                stderr="CONFLICT detected in file.txt",
            )
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert result["error_type"] == "restack_conflict"
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_submit_fails(self) -> None:
        """Test error when submit fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_submit_failure(stdout="", stderr="network error")
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert "Failed to submit update" in result["error"]
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_add_fails(self) -> None:
        """Test error when git add fails."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_uncommitted_files(["file.txt"])
            .with_add_failure()
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = execute_update_pr()

            assert result["success"] is False
            assert "Failed to stage changes" in result["error"]
        finally:
            update_module.RealGtKit = original_kit_class


class TestUpdatePrCLI:
    """Tests for update_pr CLI command."""

    def test_update_pr_cli_success(self, runner: CliRunner) -> None:
        """Test CLI command with successful execution."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_pr(123, url="https://github.com/repo/pull/123")
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = runner.invoke(update_pr)

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["success"] is True
            assert output["pr_number"] == 123
        finally:
            update_module.RealGtKit = original_kit_class

    def test_update_pr_cli_failure_exit_code(self, runner: CliRunner) -> None:
        """Test CLI command returns non-zero exit code on failure."""
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_commits(1)
            .with_restack_failure(stderr="failed")
        )

        import erk.data.kits.gt.kit_cli_commands.gt.update_pr as update_module

        original_kit_class = update_module.RealGtKit

        class FakeRealGtKit:
            def __init__(self) -> None:
                pass

            def git(self):
                return ops.git()

            def graphite(self):
                return ops.graphite()

            def github(self):
                return ops.github()

        update_module.RealGtKit = FakeRealGtKit

        try:
            result = runner.invoke(update_pr)

            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
        finally:
            update_module.RealGtKit = original_kit_class
