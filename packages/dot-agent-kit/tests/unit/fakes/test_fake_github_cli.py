"""Layer 1 tests: Fake infrastructure tests for FakeDotAgentGitHubCli.

These tests verify that the fake implementation itself works correctly.
They ensure the test infrastructure is reliable before using it to test business logic.
"""

from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli


def test_fake_github_cli_create_issue_assigns_sequential_numbers() -> None:
    """Verify fake assigns issue numbers sequentially."""
    fake = FakeDotAgentGitHubCli()

    result1 = fake.create_issue("First", "Body 1", ["label1"])
    result2 = fake.create_issue("Second", "Body 2", ["label2"])

    assert result1.success is True
    assert result1.issue_number == 1
    assert result1.issue_url == "https://github.com/owner/repo/issues/1"

    assert result2.success is True
    assert result2.issue_number == 2
    assert result2.issue_url == "https://github.com/owner/repo/issues/2"


def test_fake_github_cli_with_issue_declarative_setup() -> None:
    """Verify .with_issue() allows declarative test setup."""
    fake = FakeDotAgentGitHubCli().with_issue(42, "Test Issue", "Body content", ["bug"])

    issue = fake.get_issue(42)
    assert issue is not None
    assert issue.number == 42
    assert issue.title == "Test Issue"
    assert issue.body == "Body content"
    assert issue.labels == ["bug"]


def test_fake_github_cli_get_issue_returns_none_for_missing() -> None:
    """Verify get_issue returns None for non-existent issue."""
    fake = FakeDotAgentGitHubCli()

    issue = fake.get_issue(999)
    assert issue is None


def test_fake_github_cli_create_issue_stores_in_state() -> None:
    """Verify created issues are stored in queryable state."""
    fake = FakeDotAgentGitHubCli()

    result = fake.create_issue("Test", "Body", ["label1", "label2"])

    assert result.success is True
    issue = fake.get_issue(result.issue_number)
    assert issue is not None
    assert issue.title == "Test"
    assert issue.body == "Body"
    assert issue.labels == ["label1", "label2"]


def test_fake_github_cli_mutation_tracking_created_issues() -> None:
    """Verify mutation tracking records all created issues."""
    fake = FakeDotAgentGitHubCli()

    fake.create_issue("First", "Body 1", ["label1"])
    fake.create_issue("Second", "Body 2", [])
    fake.create_issue("Third", "Body 3", ["label3", "label4"])

    created = fake.created_issues
    assert len(created) == 3
    assert created[0] == ("First", "Body 1", ["label1"])
    assert created[1] == ("Second", "Body 2", [])
    assert created[2] == ("Third", "Body 3", ["label3", "label4"])


def test_fake_github_cli_declarative_setup_preserves_next_number() -> None:
    """Verify .with_issue() doesn't affect next issue number for create_issue()."""
    fake = FakeDotAgentGitHubCli().with_issue(100, "Existing", "Body", [])

    result = fake.create_issue("New Issue", "New Body", [])

    # Next issue number should still be 1 (declarative setup doesn't increment)
    assert result.issue_number == 1
    assert fake.get_issue(100) is not None  # Declaratively added issue still exists
    assert fake.get_issue(1) is not None  # Newly created issue exists


def test_fake_github_cli_with_issue_returns_new_instance() -> None:
    """Verify .with_issue() returns new instance (immutable pattern)."""
    fake1 = FakeDotAgentGitHubCli()
    fake2 = fake1.with_issue(42, "Test", "Body", [])

    # Original fake should not have the issue
    assert fake1.get_issue(42) is None

    # New fake should have the issue
    assert fake2.get_issue(42) is not None


def test_fake_github_cli_issues_property_returns_copy() -> None:
    """Verify .issues property returns a copy (prevents external mutation)."""
    fake = FakeDotAgentGitHubCli()
    fake.create_issue("Test", "Body", [])

    issues1 = fake.issues
    issues2 = fake.issues

    # Should be equal but not the same object
    assert issues1 == issues2
    assert issues1 is not issues2


def test_fake_github_cli_custom_next_issue_number() -> None:
    """Verify next_issue_number can be customized for specific test scenarios."""
    fake = FakeDotAgentGitHubCli(next_issue_number=1000)

    result = fake.create_issue("Test", "Body", [])

    assert result.issue_number == 1000


def test_fake_github_cli_unicode_content() -> None:
    """Verify fake handles Unicode content correctly."""
    fake = FakeDotAgentGitHubCli()
    unicode_title = "测试 Issue with émojis 🎉"
    unicode_body = "Body with Unicode: 你好世界 café"

    result = fake.create_issue(unicode_title, unicode_body, [])

    assert result.success is True
    issue = fake.get_issue(result.issue_number)
    assert issue is not None
    assert issue.title == unicode_title
    assert issue.body == unicode_body


def test_fake_github_cli_empty_labels() -> None:
    """Verify fake handles empty label list correctly."""
    fake = FakeDotAgentGitHubCli()

    result = fake.create_issue("Test", "Body", [])

    assert result.success is True
    issue = fake.get_issue(result.issue_number)
    assert issue is not None
    assert issue.labels == []
