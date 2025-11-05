"""Tests for source parsing utility."""

import pytest

from dot_agent_kit.sources.exceptions import InvalidKitIdError, SourceFormatError
from dot_agent_kit.sources.resolver import parse_source, validate_kit_id


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
    """Test parsing when identifier contains colons.

    The parse_source function splits on the first colon only, so identifiers
    can contain additional colons.
    """
    prefix, identifier = parse_source("package:foo:bar")
    assert prefix == "package"
    assert identifier == "foo:bar"


def test_parse_source_missing_prefix() -> None:
    """Test that unprefixed source raises helpful error."""
    with pytest.raises(SourceFormatError, match="Invalid source format"):
        parse_source("gt")

    with pytest.raises(SourceFormatError, match="must be prefixed"):
        parse_source("gt")


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


def test_parse_source_with_various_identifiers() -> None:
    """Test that parse_source accepts various identifier formats.

    The parse_source function only splits the source string. Validation
    of identifiers (like kit IDs) happens elsewhere when needed.
    """
    # Identifiers can contain various characters
    prefix, identifier = parse_source("bundled:MyKit")
    assert prefix == "bundled"
    assert identifier == "MyKit"

    prefix, identifier = parse_source("package:my_kit")
    assert prefix == "package"
    assert identifier == "my_kit"

    prefix, identifier = parse_source("github:owner/repo")
    assert prefix == "github"
    assert identifier == "owner/repo"
