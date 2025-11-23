"""Tests for context helper functions.

Layer 3 (Pure Unit Tests): Testing getter functions in isolation.
"""

import pytest

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.context_helpers import require_github_cli, require_github_issues


def test_require_github_cli_returns_cli_when_context_initialized() -> None:
    """Test that require_github_cli returns CLI when context is initialized."""
    from unittest.mock import MagicMock

    from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli

    # Create context and mock Click context
    github_cli = FakeDotAgentGitHubCli()
    test_ctx = DotAgentContext.for_test(github_cli=github_cli)

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx

    # Act
    result = require_github_cli(mock_click_ctx)

    # Assert
    assert result is github_cli


def test_require_github_cli_exits_when_context_none() -> None:
    """Test that require_github_cli exits with code 1 when context is None."""
    from unittest.mock import MagicMock

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_github_cli(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_github_issues_returns_issues_when_context_initialized() -> None:
    """Test that require_github_issues returns Issues when context is initialized."""
    from unittest.mock import MagicMock

    from erk.core.github.issues import FakeGitHubIssues

    # Create context and mock Click context
    github_issues = FakeGitHubIssues()
    test_ctx = DotAgentContext.for_test(github_issues=github_issues)

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx

    # Act
    result = require_github_issues(mock_click_ctx)

    # Assert
    assert result is github_issues


def test_require_github_issues_exits_when_context_none() -> None:
    """Test that require_github_issues exits with code 1 when context is None."""
    from unittest.mock import MagicMock

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_github_issues(mock_click_ctx)

    assert exc_info.value.code == 1
