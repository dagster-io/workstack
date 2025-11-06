"""Tests for KitCliCommandDefinition validation."""

from dot_agent_kit.models.kit import KitCliCommandDefinition


def test_validate_valid_definition() -> None:
    """Test validation of a valid command definition."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert errors == []


def test_validate_valid_definition_with_numbers() -> None:
    """Test validation accepts numbers in name."""
    cmd = KitCliCommandDefinition(
        name="test-command-123", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert errors == []


def test_validate_valid_nested_path() -> None:
    """Test validation accepts nested paths."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="commands/subdir/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert errors == []


def test_validate_invalid_name_uppercase() -> None:
    """Test validation rejects uppercase letters in name."""
    cmd = KitCliCommandDefinition(
        name="Test-Command", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_underscore() -> None:
    """Test validation rejects underscores in name."""
    cmd = KitCliCommandDefinition(
        name="test_command", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_starts_with_number() -> None:
    """Test validation rejects names starting with numbers."""
    cmd = KitCliCommandDefinition(
        name="123-test", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_special_chars() -> None:
    """Test validation rejects special characters in name."""
    cmd = KitCliCommandDefinition(
        name="test@command", path="commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_path_not_python() -> None:
    """Test validation rejects non-.py files."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="commands/test.txt", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must end with .py" in errors[0]


def test_validate_path_no_extension() -> None:
    """Test validation rejects paths without extension."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="commands/test", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "must end with .py" in errors[0]


def test_validate_path_traversal() -> None:
    """Test validation rejects directory traversal in path."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="../commands/test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "directory traversal" in errors[0]


def test_validate_path_traversal_middle() -> None:
    """Test validation rejects directory traversal in middle of path."""
    cmd = KitCliCommandDefinition(
        name="test-command", path="commands/../test.py", description="Test command"
    )

    errors = cmd.validate()
    assert len(errors) == 1
    assert "directory traversal" in errors[0]


def test_validate_empty_description() -> None:
    """Test validation rejects empty description."""
    cmd = KitCliCommandDefinition(name="test-command", path="commands/test.py", description="")

    errors = cmd.validate()
    assert len(errors) == 1
    assert "Description cannot be empty" in errors[0]


def test_validate_whitespace_only_description() -> None:
    """Test validation rejects whitespace-only description."""
    cmd = KitCliCommandDefinition(name="test-command", path="commands/test.py", description="   ")

    errors = cmd.validate()
    assert len(errors) == 1
    assert "Description cannot be empty" in errors[0]


def test_validate_multiple_errors() -> None:
    """Test validation returns multiple errors when multiple issues exist."""
    cmd = KitCliCommandDefinition(name="INVALID_NAME", path="../bad/path.txt", description="")

    errors = cmd.validate()
    assert len(errors) == 4  # name, path extension, path traversal, description
    assert any("must start with lowercase letter" in e for e in errors)
    assert any("must end with .py" in e for e in errors)
    assert any("directory traversal" in e for e in errors)
    assert any("Description cannot be empty" in e for e in errors)
