"""Smoke tests for real_ops.py subprocess integration.

These tests verify that real subprocess-based implementations can be called
without crashing and handle basic success/failure scenarios. Tests use actual
git/gh/gt commands as requested for code coverage.

Test organization:
- TestRealGitGtKitOpsSmoke: Git operations (6 methods)
- TestRealGraphiteGtKitOpsSmoke: Graphite operations (6 methods)
- TestRealGitHubGtKitOpsSmoke: GitHub operations (4 methods)
- TestRealGtKitOpsSmoke: Composite operations (3 accessor methods)
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops import (
    RealGitGtKitOps,
    RealGitHubGtKitOps,
    RealGraphiteGtKitOps,
    RealGtKitOps,
)


class TestRealGitGtKitOpsSmoke:
    """Smoke tests for RealGitGtKitOps subprocess integration."""

    def test_get_current_branch(self) -> None:
        """Test get_current_branch returns branch name or None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Test from repo directory
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()
                branch_name = ops.get_current_branch()

                assert branch_name is not None
                assert isinstance(branch_name, str)
                # Default branch is typically "main" or "master"
                assert branch_name in ("main", "master")
            finally:
                os.chdir(original_cwd)

    def test_has_uncommitted_changes(self) -> None:
        """Test has_uncommitted_changes returns bool correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()

                # Should be clean after commit
                assert ops.has_uncommitted_changes() is False

                # Create new file
                new_file = repo_path / "new.txt"
                new_file.write_text("new content", encoding="utf-8")

                # Should detect uncommitted changes
                assert ops.has_uncommitted_changes() is True
            finally:
                os.chdir(original_cwd)

    def test_add_all(self) -> None:
        """Test add_all returns True on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create file
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()

                # Add all files
                result = ops.add_all()

                assert result is True
            finally:
                os.chdir(original_cwd)

    def test_commit(self) -> None:
        """Test commit returns True on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create and stage file
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()

                # Create commit
                result = ops.commit("Test commit")

                assert result is True
            finally:
                os.chdir(original_cwd)

    def test_amend_commit(self) -> None:
        """Test amend_commit returns True on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Modify file and stage
            test_file.write_text("modified", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()

                # Amend commit
                result = ops.amend_commit("Amended commit")

                assert result is True
            finally:
                os.chdir(original_cwd)

    def test_count_commits_in_branch(self) -> None:
        """Test count_commits_in_branch returns int count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit on main
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Rename default branch to main (git init may create master or other name)
            subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create branch and add commits
            subprocess.run(
                ["git", "checkout", "-b", "feature"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            for i in range(3):
                new_file = repo_path / f"file{i}.txt"
                new_file.write_text(f"content{i}", encoding="utf-8")
                subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Commit {i}"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )

            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKitOps()

                # Count commits since main
                count = ops.count_commits_in_branch("main")

                assert isinstance(count, int)
                assert count == 3
            finally:
                os.chdir(original_cwd)


class TestRealGraphiteGtKitOpsSmoke:
    """Smoke tests for RealGraphiteGtKitOps subprocess integration.

    These tests call real gt commands and verify they don't crash.
    Tests may fail if gt is not installed, which is expected.
    """

    def test_get_parent_branch(self) -> None:
        """Test get_parent_branch returns str or None."""
        ops = RealGraphiteGtKitOps()

        # Call the method - may return None if not in gt repo or gt not installed
        result = ops.get_parent_branch()

        # Verify return type matches interface contract
        assert result is None or isinstance(result, str)

    def test_get_children_branches(self) -> None:
        """Test get_children_branches returns list."""
        ops = RealGraphiteGtKitOps()

        # Call the method - may return empty list if not in gt repo or gt not installed
        result = ops.get_children_branches()

        # Verify return type matches interface contract
        assert isinstance(result, list)
        # All elements should be strings if present
        if result:
            assert all(isinstance(branch, str) for branch in result)

    def test_squash_commits(self) -> None:
        """Test squash_commits returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKitOps()
            result = ops.squash_commits()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "squash"], capture_output=True, text=True, check=False
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKitOps()
            result = ops.squash_commits()
            assert result is False

    def test_submit(self) -> None:
        """Test submit returns tuple with 3 elements and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "PR created successfully"
        mock_result.stderr = ""

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKitOps()
            result = ops.submit(publish=False, restack=False)

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "submit", "--no-interactive"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert isinstance(result, tuple)
            assert len(result) == 3
            success, stdout, stderr = result
            assert isinstance(success, bool)
            assert isinstance(stdout, str)
            assert isinstance(stderr, str)
            assert success is True
            assert stdout == "PR created successfully"
            assert stderr == ""

        # Test with publish=True, restack=True
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKitOps()
            result = ops.submit(publish=True, restack=True)

            # Verify flags are added
            mock_run.assert_called_once_with(
                ["gt", "submit", "--no-interactive", "--publish", "--restack"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_restack(self) -> None:
        """Test restack returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKitOps()
            result = ops.restack()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "restack", "--no-interactive"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKitOps()
            result = ops.restack()
            assert result is False

    def test_navigate_to_child(self) -> None:
        """Test navigate_to_child returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKitOps()
            result = ops.navigate_to_child()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "up"], capture_output=True, text=True, check=False
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKitOps()
            result = ops.navigate_to_child()
            assert result is False


class TestRealGitHubGtKitOpsSmoke:
    """Smoke tests for RealGitHubGtKitOps subprocess integration.

    These tests call real gh commands and verify they don't crash.
    Tests may fail if gh is not installed or not in a repo with a PR, which is expected.
    """

    def test_get_pr_info(self) -> None:
        """Test get_pr_info returns tuple or None."""
        ops = RealGitHubGtKitOps()

        # Call the method - may return None if not in repo with PR or gh not installed
        result = ops.get_pr_info()

        # Verify return type matches interface contract
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 2
            pr_number, pr_url = result
            assert isinstance(pr_number, int)
            assert isinstance(pr_url, str)

    def test_get_pr_state(self) -> None:
        """Test get_pr_state returns tuple or None."""
        ops = RealGitHubGtKitOps()

        # Call the method - may return None if not in repo with PR or gh not installed
        result = ops.get_pr_state()

        # Verify return type matches interface contract
        if result is not None:
            assert isinstance(result, tuple)
            assert len(result) == 2
            pr_number, pr_state = result
            assert isinstance(pr_number, int)
            assert isinstance(pr_state, str)

    def test_update_pr_metadata(self) -> None:
        """Test update_pr_metadata returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKitOps()
            result = ops.update_pr_metadata("Test Title", "Test Body")

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gh", "pr", "edit", "--title", "Test Title", "--body", "Test Body"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKitOps()
            result = ops.update_pr_metadata("Title", "Body")
            assert result is False

    def test_merge_pr(self) -> None:
        """Test merge_pr returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGitHubGtKitOps()
            result = ops.merge_pr()

            # Verify correct command was called (squash merge)
            mock_run.assert_called_once_with(
                ["gh", "pr", "merge", "-s"], capture_output=True, text=True, check=False
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "dot_agent_kit.data.kits.gt.kit_cli_commands.gt.real_ops.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGitHubGtKitOps()
            result = ops.merge_pr()
            assert result is False


class TestRealGtKitOpsSmoke:
    """Smoke tests for RealGtKitOps composite operations."""

    def test_git(self) -> None:
        """Test git() returns RealGitGtKitOps instance."""
        ops = RealGtKitOps()

        # Get git operations interface
        git_ops = ops.git()

        # Verify return type matches interface contract
        assert isinstance(git_ops, RealGitGtKitOps)

    def test_graphite(self) -> None:
        """Test graphite() returns RealGraphiteGtKitOps instance."""
        ops = RealGtKitOps()

        # Get graphite operations interface
        graphite_ops = ops.graphite()

        # Verify return type matches interface contract
        assert isinstance(graphite_ops, RealGraphiteGtKitOps)

    def test_github(self) -> None:
        """Test github() returns RealGitHubGtKitOps instance."""
        ops = RealGtKitOps()

        # Get github operations interface
        github_ops = ops.github()

        # Verify return type matches interface contract
        assert isinstance(github_ops, RealGitHubGtKitOps)
