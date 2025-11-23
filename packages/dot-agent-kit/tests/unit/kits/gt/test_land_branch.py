"""Tests for land_branch kit CLI command using fake ops."""

from dataclasses import replace

import pytest
from click.testing import CliRunner

from erk.data.kits.gt.kit_cli_commands.gt.land_branch import (
    LandBranchError,
    LandBranchSuccess,
    execute_land_branch,
)
from tests.unit.kits.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestLandBranchExecution:
    """Tests for land_branch execution logic using fakes."""

    def test_land_branch_success_no_children(self) -> None:
        """Test successfully landing a branch with no children."""
        # Setup: feature branch on main with open PR
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main").with_pr(123, state="OPEN")

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchSuccess)
        assert result.success is True
        assert result.pr_number == 123
        assert result.branch_name == "feature-branch"
        assert result.child_branch is None
        assert "Successfully merged PR #123" in result.message

    def test_land_branch_success_single_child(self) -> None:
        """Test successfully landing a branch with single child (auto-navigate)."""
        # Setup: feature branch on main with PR and one child
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
            .with_children(["next-feature"])
        )

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchSuccess)
        assert result.success is True
        assert result.child_branch == "next-feature"
        assert "Navigated to child branch: next-feature" in result.message

    def test_land_branch_success_multiple_children(self) -> None:
        """Test successfully landing a branch with multiple children (no auto-navigate)."""
        # Setup: feature branch on main with PR and multiple children
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
            .with_children(["feature-a", "feature-b"])
        )

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchSuccess)
        assert result.success is True
        assert result.child_branch is None
        assert "Multiple children detected" in result.message
        assert "feature-a, feature-b" in result.message

    def test_land_branch_error_parent_not_trunk(self) -> None:
        """Test error when branch parent is not trunk."""
        # Setup: feature branch with parent other than trunk (main)
        ops = FakeGtKitOps().with_branch("feature-branch", parent="develop")

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "must be exactly one level up from main" in result.message
        assert result.details["parent_branch"] == "develop"

    def test_land_branch_error_no_parent(self) -> None:
        """Test error when parent branch cannot be determined."""
        # Setup: branch with no parent (orphaned)
        ops = FakeGtKitOps()
        # Don't set parent relationship, so get_parent_branch returns None
        ops.git()._state = replace(ops.git().get_state(), current_branch="orphan-branch")
        ops.graphite().set_current_branch("orphan-branch")
        ops.github().set_current_branch("orphan-branch")

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "Could not determine parent branch" in result.message

    def test_land_branch_error_no_pr(self) -> None:
        """Test error when no PR exists for the branch."""
        # Setup: feature branch on main but no PR
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # Don't call with_pr(), so no PR exists

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "no_pr_found"
        assert "No pull request found" in result.message
        assert "gt submit" in result.message

    def test_land_branch_error_pr_not_open(self) -> None:
        """Test error when PR exists but is not open."""
        # Setup: feature branch on main with merged PR
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_pr(123, state="MERGED")
        )

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "pr_not_open"
        assert "Pull request is not open" in result.message
        assert "MERGED" in result.message

    def test_land_branch_error_merge_failed(self) -> None:
        """Test error when PR merge fails."""
        # Setup: feature branch on main with open PR but merge configured to fail
        ops = (
            FakeGtKitOps()
            .with_branch("feature-branch", parent="main")
            .with_pr(123, state="OPEN")
            .with_merge_failure()
        )

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "merge_failed"
        assert "Failed to merge PR #123" in result.message

    def test_land_branch_with_master_trunk(self) -> None:
        """Test successfully landing a branch when trunk is 'master' instead of 'main'."""
        # Setup: feature branch on master with open PR, configure trunk as "master"
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="master").with_pr(123, state="OPEN")
        )
        # Configure git ops to return "master" as trunk
        ops.git()._state = replace(ops.git().get_state(), trunk_branch="master")

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchSuccess)
        assert result.success is True
        assert result.pr_number == 123
        assert result.branch_name == "feature-branch"

    def test_land_branch_error_parent_not_trunk_with_master(self) -> None:
        """Test error when branch parent is not trunk, with master as trunk."""
        # Setup: feature branch with parent "main" when trunk is "master"
        ops = FakeGtKitOps().with_branch("feature-branch", parent="main")
        # Configure git ops to return "master" as trunk
        ops.git()._state = replace(ops.git().get_state(), trunk_branch="master")

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.success is False
        assert result.error_type == "parent_not_trunk"
        assert "must be exactly one level up from master" in result.message
        assert result.details["parent_branch"] == "main"


class TestLandBranchCLI:
    """Tests for land_branch CLI command."""

    def test_land_branch_cli_success(self, runner: CliRunner) -> None:
        """Test CLI command with successful land."""
        # Note: CLI test uses real ops, so this would need actual git/gh setup
        # This is a placeholder showing the pattern
        # In practice, you'd either mock or use integration tests for CLI
        pass

    def test_land_branch_cli_error_output(self, runner: CliRunner) -> None:
        """Test CLI command error output format."""
        # Note: CLI test pattern placeholder
        pass


class TestLandBranchEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_land_branch_with_closed_pr(self) -> None:
        """Test landing with closed (not merged) PR."""
        ops = (
            FakeGtKitOps().with_branch("feature-branch", parent="main").with_pr(123, state="CLOSED")
        )

        result = execute_land_branch(ops)

        assert isinstance(result, LandBranchError)
        assert result.error_type == "pr_not_open"

    def test_land_branch_unknown_current_branch(self) -> None:
        """Test when current branch cannot be determined."""
        ops = FakeGtKitOps()
        # Set current_branch to empty to simulate failure
        ops.git()._state = replace(ops.git().get_state(), current_branch="")

        result = execute_land_branch(ops)

        # Should handle gracefully with "unknown" branch name
        assert isinstance(result, LandBranchError)
        assert result.details["current_branch"] == "unknown"
