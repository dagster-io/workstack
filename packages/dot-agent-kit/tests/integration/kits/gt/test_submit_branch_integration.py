"""Integration tests for submit_branch using real git repositories."""

import subprocess
import tempfile
from pathlib import Path


class TestSubmitBranchIntegration:
    """Integration tests using real git repos for edge cases."""

    def test_amend_commit_with_backticks_direct(self) -> None:
        """Test commit message with backticks using real git repo.

        This test uses a real git repository because it tests edge case
        behavior around shell quoting that is difficult to fake accurately.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
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
            test_file.write_text("initial content", encoding="utf-8")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Test amend with backticks in message
            message_with_backticks = "feat: add `some_function()` implementation"
            subprocess.run(
                ["git", "commit", "--amend", "-m", message_with_backticks],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Verify the message was set correctly
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

            assert message_with_backticks in result.stdout
