"""Tests for source parsing utility."""

import pytest

from dot_agent_kit.sources.exceptions import InvalidKitIdError
from dot_agent_kit.sources.resolver import validate_kit_id


@pytest.mark.skip(reason="parse_source not yet implemented")
def test_parse_source_bundled() -> None:
    """Test parsing bundled: prefix."""
    pass


@pytest.mark.skip(reason="parse_source not yet implemented")
def test_parse_source_package() -> None:
    """Test parsing package: prefix."""
    pass


@pytest.mark.skip(reason="parse_source not yet implemented")
def test_parse_source_with_multiple_colons() -> None:
    """Test parsing when identifier contains colons."""
    pass


@pytest.mark.skip(reason="parse_source not yet implemented")
def test_parse_source_missing_prefix() -> None:
    """Test that unprefixed source raises helpful error."""
    pass


def test_validate_kit_id() -> None:
    """Test kit ID validation."""
    # Valid kit IDs
    validate_kit_id("my-kit")
    validate_kit_id("kit-123")
    validate_kit_id("a-b-c-d")
    validate_kit_id("test")

    # Invalid kit IDs
    with pytest.raises(InvalidKitIdError, match="must only contain lowercase"):
        validate_kit_id("MyKit")  # uppercase

    with pytest.raises(InvalidKitIdError, match="must only contain lowercase"):
        validate_kit_id("my_kit")  # underscore

    with pytest.raises(InvalidKitIdError, match="must only contain lowercase"):
        validate_kit_id("my kit")  # space

    with pytest.raises(InvalidKitIdError, match="must only contain lowercase"):
        validate_kit_id("my.kit")  # dot
