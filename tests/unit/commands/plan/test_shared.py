"""Unit tests for shared plan command utilities."""

import pytest

from erk.cli.commands.plan.shared import parse_plan_identifier


def test_parse_identifier_with_number_string() -> None:
    """Should parse a simple numeric string."""
    assert parse_plan_identifier("42") == 42


def test_parse_identifier_with_large_number() -> None:
    """Should parse large issue numbers."""
    assert parse_plan_identifier("12345") == 12345


def test_parse_identifier_with_github_url() -> None:
    """Should extract issue number from full GitHub URL."""
    url = "https://github.com/owner/repo/issues/42"
    assert parse_plan_identifier(url) == 42


def test_parse_identifier_with_trailing_slash() -> None:
    """Should handle GitHub URLs with trailing slash."""
    url = "https://github.com/owner/repo/issues/42/"
    assert parse_plan_identifier(url) == 42


def test_parse_identifier_with_invalid_format() -> None:
    """Should raise ValueError for invalid identifier format."""
    with pytest.raises(ValueError, match="Invalid identifier: not-a-number"):
        parse_plan_identifier("not-a-number")


def test_parse_identifier_with_invalid_url() -> None:
    """Should raise ValueError for invalid GitHub URL."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        parse_plan_identifier("https://example.com/issues/42")


def test_parse_identifier_with_pull_request_url() -> None:
    """Should reject pull request URLs."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        parse_plan_identifier("https://github.com/owner/repo/pull/42")


def test_parse_identifier_with_malformed_url() -> None:
    """Should reject URLs without issue number."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        parse_plan_identifier("https://github.com/owner/repo/issues")
