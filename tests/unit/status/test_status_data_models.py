"""Unit tests for status data model factory methods."""

from pathlib import Path

from erk.status.models.status_data import (
    CommitInfo,
    GitStatus,
    StatusData,
    WorktreeDisplayInfo,
)
from tests.helpers.commits import make_test_commits


def test_worktree_display_info_root_factory() -> None:
    """Test WorktreeDisplayInfo.root() factory method."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path)

    # Assert
    assert worktree.path == path
    assert worktree.branch == "main"
    assert worktree.name == "root"
    assert worktree.is_root is True


def test_worktree_display_info_root_factory_custom_branch() -> None:
    """Test WorktreeDisplayInfo.root() with custom branch."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path, branch="master")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "master"
    assert worktree.name == "root"
    assert worktree.is_root is True


def test_worktree_display_info_root_factory_custom_name() -> None:
    """Test WorktreeDisplayInfo.root() with custom name."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path, name="custom-root")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "main"
    assert worktree.name == "custom-root"
    assert worktree.is_root is True


def test_worktree_display_info_feature_factory() -> None:
    """Test WorktreeDisplayInfo.feature() factory method."""
    # Arrange
    path = Path("/tmp/my-feature")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "feature-branch")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "feature-branch"
    assert worktree.name == "my-feature"  # Uses path.name
    assert worktree.is_root is False


def test_worktree_display_info_feature_factory_custom_name() -> None:
    """Test WorktreeDisplayInfo.feature() with custom name."""
    # Arrange
    path = Path("/tmp/feature-worktree")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "feature-branch", name="custom-name")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "feature-branch"
    assert worktree.name == "custom-name"
    assert worktree.is_root is False


def test_worktree_display_info_feature_uses_path_name_by_default() -> None:
    """Test WorktreeDisplayInfo.feature() defaults to path.name for display name."""
    # Arrange
    path = Path("/some/long/path/my-worktree-name")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "branch")

    # Assert
    assert worktree.name == "my-worktree-name"
    assert worktree.is_root is False


# GitStatus Factory Method Tests


def test_git_status_clean_status_factory() -> None:
    """Test GitStatus.clean_status() factory method."""
    # Act
    status = GitStatus.clean_status("main")

    # Assert
    assert status.branch == "main"
    assert status.clean is True
    assert status.ahead == 0
    assert status.behind == 0
    assert status.staged_files == []
    assert status.modified_files == []
    assert status.untracked_files == []
    assert status.recent_commits == []


def test_git_status_clean_status_factory_with_ahead_behind() -> None:
    """Test GitStatus.clean_status() with ahead/behind counts."""
    # Act
    status = GitStatus.clean_status("feature", ahead=2, behind=1)

    # Assert
    assert status.branch == "feature"
    assert status.clean is True
    assert status.ahead == 2
    assert status.behind == 1
    assert status.staged_files == []
    assert status.modified_files == []
    assert status.untracked_files == []


def test_git_status_dirty_status_factory_with_modified() -> None:
    """Test GitStatus.dirty_status() with modified files."""
    # Act
    status = GitStatus.dirty_status("feature", modified=["file.py", "other.py"])

    # Assert
    assert status.branch == "feature"
    assert status.clean is False
    assert status.modified_files == ["file.py", "other.py"]
    assert status.staged_files == []
    assert status.untracked_files == []
    assert status.recent_commits == []


def test_git_status_dirty_status_factory_with_staged() -> None:
    """Test GitStatus.dirty_status() with staged files."""
    # Act
    status = GitStatus.dirty_status("feature", staged=["staged.py"])

    # Assert
    assert status.branch == "feature"
    assert status.clean is False
    assert status.staged_files == ["staged.py"]
    assert status.modified_files == []
    assert status.untracked_files == []


def test_git_status_dirty_status_factory_with_untracked() -> None:
    """Test GitStatus.dirty_status() with untracked files."""
    # Act
    status = GitStatus.dirty_status("feature", untracked=["new.py", "temp.txt"])

    # Assert
    assert status.branch == "feature"
    assert status.clean is False
    assert status.untracked_files == ["new.py", "temp.txt"]
    assert status.staged_files == []
    assert status.modified_files == []


def test_git_status_dirty_status_factory_with_all_changes() -> None:
    """Test GitStatus.dirty_status() with all change types."""
    # Act
    status = GitStatus.dirty_status(
        "feature",
        modified=["mod.py"],
        staged=["staged.py"],
        untracked=["new.py"],
        ahead=1,
        behind=2,
    )

    # Assert
    assert status.branch == "feature"
    assert status.clean is False
    assert status.modified_files == ["mod.py"]
    assert status.staged_files == ["staged.py"]
    assert status.untracked_files == ["new.py"]
    assert status.ahead == 1
    assert status.behind == 2


def test_git_status_with_commits_factory() -> None:
    """Test GitStatus.with_commits() factory method."""
    # Arrange
    commit1 = CommitInfo(sha="abc123", message="First", author="Author", date="1 day ago")
    commit2 = CommitInfo(sha="def456", message="Second", author="Author", date="2 days ago")

    # Act
    status = GitStatus.with_commits("main", [commit1, commit2])

    # Assert
    assert status.branch == "main"
    assert status.clean is True
    assert status.recent_commits == [commit1, commit2]
    assert status.staged_files == []
    assert status.modified_files == []
    assert status.untracked_files == []


def test_git_status_with_commits_factory_dirty() -> None:
    """Test GitStatus.with_commits() with dirty working tree."""
    # Arrange
    commit = CommitInfo(sha="abc123", message="Test", author="Author", date="1 hour ago")

    # Act
    status = GitStatus.with_commits("feature", [commit], clean=False)

    # Assert
    assert status.branch == "feature"
    assert status.clean is False
    assert status.recent_commits == [commit]


# StatusData Factory Method Tests


def test_status_data_minimal_factory() -> None:
    """Test StatusData.minimal() factory method."""
    # Arrange
    worktree_info = WorktreeDisplayInfo.feature(Path("/tmp/my-feature"), "feature")

    # Act
    status_data = StatusData.minimal(worktree_info)

    # Assert
    assert status_data.worktree_info == worktree_info
    assert status_data.git_status is None
    assert status_data.stack_position is None
    assert status_data.pr_status is None
    assert status_data.environment is None
    assert status_data.dependencies is None
    assert status_data.plan is None
    assert status_data.related_worktrees == []


def test_status_data_with_git_status_factory() -> None:
    """Test StatusData.with_git_status() factory method."""
    # Arrange
    worktree_info = WorktreeDisplayInfo.root(Path("/tmp/repo"))
    git_status = GitStatus.clean_status("main")

    # Act
    status_data = StatusData.with_git_status(worktree_info, git_status)

    # Assert
    assert status_data.worktree_info == worktree_info
    assert status_data.git_status == git_status
    assert status_data.stack_position is None
    assert status_data.pr_status is None
    assert status_data.environment is None
    assert status_data.dependencies is None
    assert status_data.plan is None
    assert status_data.related_worktrees == []


def test_status_data_with_git_status_factory_with_dirty_status() -> None:
    """Test StatusData.with_git_status() with dirty git status."""
    # Arrange
    worktree_info = WorktreeDisplayInfo.feature(Path("/tmp/feature"), "feature-1")
    git_status = GitStatus.dirty_status("feature-1", modified=["file.py"], staged=["other.py"])

    # Act
    status_data = StatusData.with_git_status(worktree_info, git_status)

    # Assert
    assert status_data.worktree_info == worktree_info
    assert status_data.git_status == git_status
    assert status_data.git_status.clean is False
    assert status_data.git_status.modified_files == ["file.py"]
    assert status_data.git_status.staged_files == ["other.py"]
    assert status_data.stack_position is None
    assert status_data.pr_status is None


# CommitInfo Factory Method Tests


def test_commit_info_test_commit_factory() -> None:
    """Test CommitInfo.test_commit() factory method with defaults."""
    # Act
    commit = CommitInfo.test_commit()

    # Assert
    assert commit.sha == "abc1234"
    assert commit.message == "Test commit"
    assert commit.author == "Test User"
    assert commit.date == "1 hour ago"


def test_commit_info_test_commit_factory_custom_sha() -> None:
    """Test CommitInfo.test_commit() with custom SHA."""
    # Act
    commit = CommitInfo.test_commit(sha="custom123")

    # Assert
    assert commit.sha == "custom123"
    assert commit.message == "Test commit"
    assert commit.author == "Test User"
    assert commit.date == "1 hour ago"


def test_commit_info_test_commit_factory_custom_message() -> None:
    """Test CommitInfo.test_commit() with custom message."""
    # Act
    commit = CommitInfo.test_commit(message="Custom commit message")

    # Assert
    assert commit.sha == "abc1234"
    assert commit.message == "Custom commit message"
    assert commit.author == "Test User"
    assert commit.date == "1 hour ago"


def test_commit_info_test_commit_factory_all_custom() -> None:
    """Test CommitInfo.test_commit() with all custom fields."""
    # Act
    commit = CommitInfo.test_commit(
        sha="xyz789",
        message="Important change",
        author="Custom Author",
        date="2 days ago",
    )

    # Assert
    assert commit.sha == "xyz789"
    assert commit.message == "Important change"
    assert commit.author == "Custom Author"
    assert commit.date == "2 days ago"


def test_make_test_commits_helper_default_count() -> None:
    """Test make_test_commits() helper with default count."""
    # Act
    commits = make_test_commits()

    # Assert
    assert len(commits) == 3
    assert commits[0].sha == "abc0001"
    assert commits[0].message == "Test commit 1"
    assert commits[1].sha == "abc0002"
    assert commits[1].message == "Test commit 2"
    assert commits[2].sha == "abc0003"
    assert commits[2].message == "Test commit 3"


def test_make_test_commits_helper_custom_count() -> None:
    """Test make_test_commits() helper with custom count."""
    # Act
    commits = make_test_commits(count=5)

    # Assert
    assert len(commits) == 5
    assert commits[0].sha == "abc0001"
    assert commits[4].sha == "abc0005"
    assert commits[4].message == "Test commit 5"


def test_make_test_commits_helper_unique_data() -> None:
    """Test make_test_commits() generates unique SHAs and messages."""
    # Act
    commits = make_test_commits(count=10)

    # Assert
    shas = [c.sha for c in commits]
    messages = [c.message for c in commits]
    assert len(set(shas)) == 10  # All SHAs unique
    assert len(set(messages)) == 10  # All messages unique
