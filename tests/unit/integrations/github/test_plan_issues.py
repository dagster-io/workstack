"""Unit tests for plan issue utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from erk.integrations.github.plan_issues import wrap_plan_with_context


class TestWrapPlanWithContext:
    """Tests for wrap_plan_with_context function."""

    def test_wrap_plan_adds_git_context(self, tmp_path: Path) -> None:
        """Test that plan content is wrapped with git context metadata."""
        plan_content = "# My Plan\n\nThis is my implementation plan."

        # Mock the git context collection
        with patch("erk.integrations.github.plan_issues.collect_plan_git_context") as mock_collect:
            mock_collect.return_value = {
                "base_commit": "abc123def456789012345678901234567890123",
                "branch": "feature-branch",
                "recent_commits": [
                    {
                        "sha": "abc123",
                        "message": "Recent change",
                        "author": "Developer",
                        "date": "1 hour ago",
                    }
                ],
                "timestamp": "2025-11-22T19:00:00Z",
            }

            result = wrap_plan_with_context(plan_content, tmp_path)

            # Verify the plan content is preserved
            assert "# My Plan" in result
            assert "This is my implementation plan." in result

            # Verify git context metadata block is added
            assert "<details>" in result
            assert "<summary><code>erk-plan-context</code></summary>" in result
            assert "base_commit:" in result
            assert "branch:" in result
            assert "recent_commits:" in result
            assert "timestamp:" in result

            # Verify order: plan first, then metadata
            plan_index = result.index("# My Plan")
            metadata_index = result.index("<summary><code>erk-plan-context</code></summary>")
            assert plan_index < metadata_index

    def test_wrap_plan_propagates_git_errors(self, tmp_path: Path) -> None:
        """Test that git context collection errors are propagated."""
        plan_content = "# My Plan"

        with patch("erk.integrations.github.plan_issues.collect_plan_git_context") as mock_collect:
            # Simulate detached HEAD error
            mock_collect.side_effect = ValueError(
                "Cannot collect git context in detached HEAD state"
            )

            with pytest.raises(ValueError) as exc_info:
                wrap_plan_with_context(plan_content, tmp_path)

            assert "detached HEAD" in str(exc_info.value)

    def test_wrap_plan_with_empty_repo_error(self, tmp_path: Path) -> None:
        """Test handling of empty repository error."""
        plan_content = "# My Plan"

        with patch("erk.integrations.github.plan_issues.collect_plan_git_context") as mock_collect:
            # Simulate empty repo error
            mock_collect.side_effect = ValueError(
                "Cannot collect git context from empty repository"
            )

            with pytest.raises(ValueError) as exc_info:
                wrap_plan_with_context(plan_content, tmp_path)

            assert "empty repository" in str(exc_info.value)

    def test_wrap_plan_preserves_complex_formatting(self, tmp_path: Path) -> None:
        """Test that complex markdown formatting is preserved."""
        plan_content = """# Implementation Plan

## Phase 1: Setup
- Create directory structure
- Initialize configuration

## Phase 2: Implementation
1. Add core functionality
2. Write tests
3. Update documentation

```python
def example():
    return "code block preserved"
```

**Note:** Special characters like @#$% and emojis 🔥✅ are preserved."""

        with patch("erk.integrations.github.plan_issues.collect_plan_git_context") as mock_collect:
            mock_collect.return_value = {
                "base_commit": "abc123",
                "branch": "main",
                "recent_commits": [],
                "timestamp": "2025-11-22T19:00:00Z",
            }

            result = wrap_plan_with_context(plan_content, tmp_path)

            # Verify all formatting is preserved
            assert "## Phase 1: Setup" in result
            assert "1. Add core functionality" in result
            assert "```python" in result
            assert 'return "code block preserved"' in result
            assert "@#$%" in result
            assert "🔥✅" in result
