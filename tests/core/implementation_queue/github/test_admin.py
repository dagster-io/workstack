"""Unit tests for GitHubAdmin implementations."""

from pathlib import Path

from tests.fakes.github_admin import FakeGitHubAdmin


def test_get_workflow_permissions_fake() -> None:
    """Test getting workflow permissions returns configured state."""
    admin = FakeGitHubAdmin(
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        }
    )
    repo_root = Path("/test/repo")

    result = admin.get_workflow_permissions(repo_root)

    assert result["default_workflow_permissions"] == "read"
    assert result["can_approve_pull_request_reviews"] is True


def test_set_workflow_pr_permissions_enable() -> None:
    """Test enabling PR permissions tracks mutation."""
    admin = FakeGitHubAdmin()
    repo_root = Path("/test/repo")

    # Verify initial state (disabled)
    perms = admin.get_workflow_permissions(repo_root)
    assert perms["can_approve_pull_request_reviews"] is False

    # Enable permissions
    admin.set_workflow_pr_permissions(repo_root, enabled=True)

    # Verify mutation was tracked
    assert len(admin.set_permission_calls) == 1
    assert admin.set_permission_calls[0] == (repo_root, True)

    # Verify internal state was updated
    perms = admin.get_workflow_permissions(repo_root)
    assert perms["can_approve_pull_request_reviews"] is True


def test_set_workflow_pr_permissions_disable() -> None:
    """Test disabling PR permissions tracks mutation."""
    admin = FakeGitHubAdmin(
        workflow_permissions={
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        }
    )
    repo_root = Path("/test/repo")

    # Disable permissions
    admin.set_workflow_pr_permissions(repo_root, enabled=False)

    # Verify mutation was tracked
    assert len(admin.set_permission_calls) == 1
    assert admin.set_permission_calls[0] == (repo_root, False)

    # Verify internal state was updated
    perms = admin.get_workflow_permissions(repo_root)
    assert perms["can_approve_pull_request_reviews"] is False


def test_multiple_permission_changes() -> None:
    """Test multiple permission changes are all tracked."""
    admin = FakeGitHubAdmin()
    repo_root = Path("/test/repo")

    # Make multiple changes
    admin.set_workflow_pr_permissions(repo_root, enabled=True)
    admin.set_workflow_pr_permissions(repo_root, enabled=False)
    admin.set_workflow_pr_permissions(repo_root, enabled=True)

    # Verify all mutations were tracked
    assert len(admin.set_permission_calls) == 3
    assert admin.set_permission_calls[0] == (repo_root, True)
    assert admin.set_permission_calls[1] == (repo_root, False)
    assert admin.set_permission_calls[2] == (repo_root, True)

    # Final state should match last change
    perms = admin.get_workflow_permissions(repo_root)
    assert perms["can_approve_pull_request_reviews"] is True
