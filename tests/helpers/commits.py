"""Helper functions for creating test commits."""

from workstack.status.models.status_data import CommitInfo


def make_test_commits(count: int = 3) -> list[CommitInfo]:
    """Create a list of test commits with unique data.

    Args:
        count: Number of commits to create (default: 3)

    Returns:
        List of CommitInfo instances with unique SHAs and messages

    Example:
        Before (5+ lines):
            commits = [
                CommitInfo(sha="abc0001", message="Commit 1",
                           author="Test User", date="1 hour ago"),
                CommitInfo(sha="abc0002", message="Commit 2",
                           author="Test User", date="2 hours ago"),
                CommitInfo(sha="abc0003", message="Commit 3",
                           author="Test User", date="3 hours ago"),
            ]

        After (1 line):
            commits = make_test_commits(3)
    """
    return [
        CommitInfo.test_commit(
            sha=f"abc{i:04d}",
            message=f"Test commit {i}",
        )
        for i in range(1, count + 1)
    ]
