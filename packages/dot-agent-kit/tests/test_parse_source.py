"""Tests for source parsing utility."""

import pytest

from dot_agent_kit.sources.resolver import parse_source


def test_parse_source_bundled() -> None:
    """Test parsing bundled: prefix."""
    prefix, identifier = parse_source("bundled:gt")
    assert prefix == "bundled"
    assert identifier == "gt"


def test_parse_source_package() -> None:
    """Test parsing package: prefix."""
    prefix, identifier = parse_source("package:my-package")
    assert prefix == "package"
    assert identifier == "my-package"


def test_parse_source_with_multiple_colons() -> None:
    """Test parsing when identifier contains colons."""
    prefix, identifier = parse_source("package:foo:bar")
    assert prefix == "package"
    assert identifier == "foo:bar"


def test_parse_source_missing_prefix() -> None:
    """Test that unprefixed source raises helpful error."""
    with pytest.raises(ValueError, match="Invalid source format"):
        parse_source("gt")

    with pytest.raises(ValueError, match="bundled:gt"):
        parse_source("gt")
