"""Test GT command tree formatting functions.

This module tests the tree visualization functions used by the GT command
to display branch hierarchies in a tree format.
"""

from pathlib import Path

from tests.fakes.gitops import FakeGitOps
from workstack.cli.commands.gt import _format_branch_recursive, _format_branches_as_tree
from workstack.core.branch_metadata import BranchMetadata


def test_format_branches_as_tree_simple_hierarchy() -> None:
    """Test tree formatting with simple branch hierarchy."""
    # Arrange: Simple hierarchy with one root and two children
    branches = {
        "main": BranchMetadata.main(children=["feature-1", "feature-2"], sha="abc123456"),
        "feature-1": BranchMetadata.branch("feature-1", sha="def456789"),
        "feature-2": BranchMetadata.branch("feature-2", sha="ghi789012"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "abc123456": "Initial commit",
            "def456789": "Add feature 1",
            "ghi789012": "Add feature 2",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Verify tree structure
    lines = tree.split("\n")
    assert len(lines) == 3
    assert 'main (abc1234) "Initial commit"' in lines[0]
    assert '├─ feature-1 (def4567) "Add feature 1"' in lines[1]
    assert '└─ feature-2 (ghi7890) "Add feature 2"' in lines[2]


def test_format_branches_as_tree_complex_hierarchy() -> None:
    """Test tree formatting with complex branch hierarchies."""
    # Arrange: Complex hierarchy with nested branches
    branches = {
        "main": BranchMetadata.main(children=["feature-1", "feature-2"], sha="aaa111111"),
        "feature-1": BranchMetadata.branch(
            "feature-1", children=["feature-1-a", "feature-1-b"], sha="bbb222222"
        ),
        "feature-1-a": BranchMetadata.branch("feature-1-a", parent="feature-1", sha="ccc333333"),
        "feature-1-b": BranchMetadata.branch("feature-1-b", parent="feature-1", sha="ddd444444"),
        "feature-2": BranchMetadata.branch(
            "feature-2", children=["feature-2-sub"], sha="eee555555"
        ),
        "feature-2-sub": BranchMetadata.branch(
            "feature-2-sub", parent="feature-2", sha="fff666666"
        ),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "aaa111111": "Main branch",
            "bbb222222": "Feature 1 base",
            "ccc333333": "Feature 1 variant A",
            "ddd444444": "Feature 1 variant B",
            "eee555555": "Feature 2 base",
            "fff666666": "Feature 2 subfeature",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Verify nested structure
    lines = tree.split("\n")
    assert len(lines) == 6
    assert 'main (aaa1111) "Main branch"' in lines[0]
    assert '├─ feature-1 (bbb2222) "Feature 1 base"' in lines[1]
    assert '│  ├─ feature-1-a (ccc3333) "Feature 1 variant A"' in lines[2]
    assert '│  └─ feature-1-b (ddd4444) "Feature 1 variant B"' in lines[3]
    assert '└─ feature-2 (eee5555) "Feature 2 base"' in lines[4]
    assert '   └─ feature-2-sub (fff6666) "Feature 2 subfeature"' in lines[5]


def test_format_branches_as_tree_deep_nesting() -> None:
    """Test tree formatting with deeply nested branches."""
    # Arrange: Deep linear nesting
    branches = {
        "main": BranchMetadata.main(children=["level-1"], sha="a1111111"),
        "level-1": BranchMetadata.branch("level-1", children=["level-2"], sha="b2222222"),
        "level-2": BranchMetadata.branch(
            "level-2", parent="level-1", children=["level-3"], sha="c3333333"
        ),
        "level-3": BranchMetadata.branch(
            "level-3", parent="level-2", children=["level-4"], sha="d4444444"
        ),
        "level-4": BranchMetadata.branch("level-4", parent="level-3", sha="e5555555"),
    }

    commit_messages = {}
    for i in range(5):
        commit_messages[f"{chr(97 + i)}{str(i + 1) * 7}"] = f"Level {i} commit"
    git_ops = FakeGitOps(commit_messages=commit_messages)

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Verify deep nesting with proper indentation
    lines = tree.split("\n")
    assert len(lines) == 5
    assert 'main (a111111) "Level 0 commit"' in lines[0]
    assert '└─ level-1 (b222222) "Level 1 commit"' in lines[1]
    assert '   └─ level-2 (c333333) "Level 2 commit"' in lines[2]
    assert '      └─ level-3 (d444444) "Level 3 commit"' in lines[3]
    assert '         └─ level-4 (e555555) "Level 4 commit"' in lines[4]


def test_format_branches_as_tree_multiple_roots() -> None:
    """Test tree formatting with multiple root branches."""
    # Arrange: Multiple trunk branches
    branches = {
        "main": BranchMetadata.main(children=["feature-1"], sha="aaa111111"),
        "develop": BranchMetadata.main("develop", children=["feature-2"], sha="bbb222222"),
        "feature-1": BranchMetadata.branch("feature-1", sha="ccc333333"),
        "feature-2": BranchMetadata.branch("feature-2", parent="develop", sha="ddd444444"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "aaa111111": "Main trunk",
            "bbb222222": "Develop trunk",
            "ccc333333": "Feature on main",
            "ddd444444": "Feature on develop",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Verify multiple roots
    lines = tree.split("\n")
    assert len(lines) == 4
    # First root and its children
    assert 'main (aaa1111) "Main trunk"' in lines[0]
    assert '└─ feature-1 (ccc3333) "Feature on main"' in lines[1]
    # Second root and its children
    assert 'develop (bbb2222) "Develop trunk"' in lines[2]
    assert '└─ feature-2 (ddd4444) "Feature on develop"' in lines[3]


def test_format_branches_as_tree_with_root_branch() -> None:
    """Test tree formatting when specifying a root branch."""
    # Arrange: Complex tree but we'll filter to show only part
    branches = {
        "main": BranchMetadata.main(children=["feature-1", "feature-2"], sha="aaa111111"),
        "feature-1": BranchMetadata.branch("feature-1", children=["sub-1"], sha="bbb222222"),
        "feature-2": BranchMetadata.branch("feature-2", children=["sub-2"], sha="ccc333333"),
        "sub-1": BranchMetadata.branch("sub-1", parent="feature-1", sha="ddd444444"),
        "sub-2": BranchMetadata.branch("sub-2", parent="feature-2", sha="eee555555"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "bbb222222": "Feature 1",
            "ddd444444": "Sub 1",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format tree with feature-1 as root
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch="feature-1")

    # Assert: Should only show feature-1 and its descendants
    lines = tree.split("\n")
    assert len(lines) == 2
    assert 'feature-1 (bbb2222) "Feature 1"' in lines[0]
    assert '└─ sub-1 (ddd4444) "Sub 1"' in lines[1]
    # Should not contain feature-2 or main
    assert "feature-2" not in tree
    assert "main" not in tree


def test_format_branch_recursive_base_case() -> None:
    """Test recursive formatting with single branch (base case)."""
    # Arrange: Single branch
    branches = {
        "main": BranchMetadata.main(sha="abc123456"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "abc123456": "Main commit",
        }
    )

    repo_root = Path("/test/repo")
    lines: list[str] = []

    # Act: Format single branch
    _format_branch_recursive(
        branch_name="main",
        branches=branches,
        git_ops=git_ops,
        repo_root=repo_root,
        lines=lines,
        prefix="",
        is_last=True,
        is_root=True,
    )

    # Assert: Single line with no connectors for root
    assert len(lines) == 1
    assert lines[0] == 'main (abc1234) "Main commit"'


def test_format_branch_recursive_with_children() -> None:
    """Test recursive formatting with branch that has children."""
    # Arrange: Branch with two children
    branches = {
        "parent": BranchMetadata.main("parent", children=["child-1", "child-2"], sha="aaa111111"),
        "child-1": BranchMetadata.branch("child-1", parent="parent", sha="bbb222222"),
        "child-2": BranchMetadata.branch("child-2", parent="parent", sha="ccc333333"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "aaa111111": "Parent",
            "bbb222222": "Child 1",
            "ccc333333": "Child 2",
        }
    )

    repo_root = Path("/test/repo")
    lines: list[str] = []

    # Act: Format parent and children
    _format_branch_recursive(
        branch_name="parent",
        branches=branches,
        git_ops=git_ops,
        repo_root=repo_root,
        lines=lines,
        prefix="",
        is_last=True,
        is_root=True,
    )

    # Assert: Parent and both children formatted correctly
    assert len(lines) == 3
    assert lines[0] == 'parent (aaa1111) "Parent"'
    # Root's children get spacing prefix
    assert lines[1] == '   ├─ child-1 (bbb2222) "Child 1"'
    assert lines[2] == '   └─ child-2 (ccc3333) "Child 2"'


def test_format_branch_recursive_missing_branch() -> None:
    """Test recursive formatting handles missing branch gracefully."""
    # Arrange: Empty branches dict
    branches: dict[str, BranchMetadata] = {}

    git_ops = FakeGitOps()
    repo_root = Path("/test/repo")
    lines: list[str] = []

    # Act: Try to format non-existent branch
    _format_branch_recursive(
        branch_name="missing",
        branches=branches,
        git_ops=git_ops,
        repo_root=repo_root,
        lines=lines,
        prefix="",
        is_last=True,
        is_root=True,
    )

    # Assert: No lines added
    assert len(lines) == 0


def test_format_branches_as_tree_empty() -> None:
    """Test tree formatting with empty branches."""
    # Arrange: Empty branches
    branches: dict[str, BranchMetadata] = {}
    git_ops = FakeGitOps()
    repo_root = Path("/test/repo")

    # Act: Format empty tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Appropriate message
    assert tree == "No branches found"


def test_format_branches_as_tree_invalid_root_branch() -> None:
    """Test tree formatting with invalid root branch specified."""
    # Arrange: Branches without requested root
    branches = {
        "main": BranchMetadata.main(sha="abc123456"),
    }

    git_ops = FakeGitOps()
    repo_root = Path("/test/repo")

    # Act: Request non-existent branch
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch="nonexistent")

    # Assert: Error message
    assert tree == "Error: Branch 'nonexistent' not found"


def test_format_branches_as_tree_no_trunks() -> None:
    """Test tree formatting when no trunk branches exist."""
    # Arrange: All branches have parents (no trunk)
    branches = {
        "feature-1": BranchMetadata.branch("feature-1", sha="abc123456"),
    }

    git_ops = FakeGitOps()
    repo_root = Path("/test/repo")

    # Act: Format without trunk branches
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: No branches message (since no roots found)
    assert tree == "No branches found"


def test_format_branch_recursive_with_mixed_children() -> None:
    """Test recursive formatting with mix of leaf and non-leaf children."""
    # Arrange: Complex mix
    branches = {
        "main": BranchMetadata.main(
            children=["feature-1", "feature-2", "feature-3"], sha="aaa111111"
        ),
        "feature-1": BranchMetadata(
            name="feature-1",
            parent="main",
            children=["feature-1-sub"],  # Has child
            is_trunk=False,
            commit_sha="bbb222222",
        ),
        "feature-1-sub": BranchMetadata.branch(
            "feature-1-sub", parent="feature-1", sha="ccc333333"
        ),
        "feature-2": BranchMetadata(
            name="feature-2",
            parent="main",
            children=[],  # No children
            is_trunk=False,
            commit_sha="ddd444444",
        ),
        "feature-3": BranchMetadata(
            name="feature-3",
            parent="main",
            children=["feature-3-a", "feature-3-b"],  # Multiple children
            is_trunk=False,
            commit_sha="eee555555",
        ),
        "feature-3-a": BranchMetadata.branch("feature-3-a", parent="feature-3", sha="fff666666"),
        "feature-3-b": BranchMetadata.branch("feature-3-b", parent="feature-3", sha="ggg777777"),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "aaa111111": "Main",
            "bbb222222": "Feature 1",
            "ccc333333": "Feature 1 sub",
            "ddd444444": "Feature 2",
            "eee555555": "Feature 3",
            "fff666666": "Feature 3a",
            "ggg777777": "Feature 3b",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format entire tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Complex structure preserved
    lines = tree.split("\n")
    assert len(lines) == 7
    assert 'main (aaa1111) "Main"' in lines[0]
    assert '├─ feature-1 (bbb2222) "Feature 1"' in lines[1]
    assert '│  └─ feature-1-sub (ccc3333) "Feature 1 sub"' in lines[2]
    assert '├─ feature-2 (ddd4444) "Feature 2"' in lines[3]
    assert '└─ feature-3 (eee5555) "Feature 3"' in lines[4]
    assert '   ├─ feature-3-a (fff6666) "Feature 3a"' in lines[5]
    assert '   └─ feature-3-b (ggg7777) "Feature 3b"' in lines[6]


def test_format_branches_with_missing_commit_message() -> None:
    """Test tree formatting when commit messages are missing."""
    # Arrange: Branch without commit message
    branches = {
        "main": BranchMetadata.main(sha="abc123456"),
    }

    git_ops = FakeGitOps()
    # Don't add commit message for this SHA - test default message behavior

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Uses default message
    assert 'main (abc1234) "No commit message"' in tree


def test_format_branches_with_no_commit_sha() -> None:
    """Test tree formatting when commit SHA is None."""
    # Arrange: Branch without SHA
    branches = {
        "main": BranchMetadata.main(sha=None),
    }

    git_ops = FakeGitOps()
    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Uses "unknown" for SHA
    assert 'main (unknown) "No commit message"' in tree


def test_format_branches_with_special_characters() -> None:
    """Test tree formatting with branch names containing special characters."""
    # Arrange: Branches with various special chars
    branches = {
        "feature/test-123": BranchMetadata.main(
            "feature/test-123", children=["bug#456", "hotfix-@special"], sha="aaa111111"
        ),
        "bug#456": BranchMetadata.branch("bug#456", parent="feature/test-123", sha="bbb222222"),
        "hotfix-@special": BranchMetadata.branch(
            "hotfix-@special", parent="feature/test-123", sha="ccc333333"
        ),
    }

    git_ops = FakeGitOps(
        commit_messages={
            "aaa111111": "Feature with special chars",
            "bbb222222": "Bug fix #456",
            "ccc333333": "Special hotfix",
        }
    )

    repo_root = Path("/test/repo")

    # Act: Format tree
    tree = _format_branches_as_tree(branches, git_ops, repo_root, root_branch=None)

    # Assert: Special characters preserved
    lines = tree.split("\n")
    assert "feature/test-123" in lines[0]
    assert "bug#456" in lines[1]
    assert "hotfix-@special" in lines[2]
