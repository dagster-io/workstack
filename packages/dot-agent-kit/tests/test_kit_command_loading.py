"""Tests for kit command loading with error isolation and lazy loading."""

from pathlib import Path

import click
import pytest

from dot_agent_kit.commands.run.group import (
    LazyKitGroup,
    _load_single_kit_commands,
)
from dot_agent_kit.models.kit import CommandDefinition, KitManifest


@pytest.fixture
def valid_manifest() -> KitManifest:
    """Create a valid kit manifest with commands."""
    return KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="test-command",
                path="commands/test_command.py",
                description="A test command",
            )
        ],
    )


@pytest.fixture
def empty_manifest() -> KitManifest:
    """Create a kit manifest with no commands."""
    return KitManifest(
        name="empty-kit",
        version="1.0.0",
        description="Empty kit",
        artifacts={},
        commands=[],
    )


@pytest.fixture
def invalid_command_manifest() -> KitManifest:
    """Create a manifest with invalid command definition."""
    return KitManifest(
        name="invalid-kit",
        version="1.0.0",
        description="Invalid kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="INVALID_NAME",  # Uppercase not allowed
                path="commands/test.py",
                description="Invalid command",
            )
        ],
    )


def test_load_valid_kit(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading a valid kit with all commands successfully."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()

    # Create the command file
    (commands_dir / "test_command.py").write_text(
        """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Hello')
""",
        encoding="utf-8",
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is not None
    assert isinstance(kit_group, LazyKitGroup)
    assert kit_group.name == "test-kit"


def test_load_kit_with_invalid_command_name(
    tmp_path: Path, invalid_command_manifest: KitManifest
) -> None:
    """Test loading kit with invalid command name logs error and continues."""
    kit_dir = tmp_path / "invalid-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_commands(
        kit_name="invalid-kit",
        kit_dir=kit_dir,
        manifest=invalid_command_manifest,
        debug=False,
    )

    # Kit group is created but commands won't load
    assert kit_group is not None


def test_load_kit_with_missing_file(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when command file doesn't exist."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    # Note: NOT creating the commands directory or file

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_load_kit_with_import_error(tmp_path: Path) -> None:
    """Test loading kit when Python import fails."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()

    # Create a file with a syntax error
    (commands_dir / "test_command.py").write_text(
        """import click

this is not valid python syntax!!!
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="test-command",
                path="commands/test_command.py",
                description="Test command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_load_kit_with_missing_function(tmp_path: Path) -> None:
    """Test loading kit when function not found in module."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()

    # Create file without the expected function
    (commands_dir / "test_command.py").write_text(
        """import click

# Missing the test_command function!
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="test-command",
                path="commands/test_command.py",
                description="Test command",
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    # Kit group is created but command won't load
    assert kit_group is not None


def test_empty_kit_not_registered(tmp_path: Path, empty_manifest: KitManifest) -> None:
    """Test that kits with no commands return None."""
    kit_dir = tmp_path / "empty-kit"
    kit_dir.mkdir()

    kit_group = _load_single_kit_commands(
        kit_name="empty-kit", kit_dir=kit_dir, manifest=empty_manifest, debug=False
    )

    assert kit_group is None


def test_kit_directory_missing(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test loading kit when kit directory doesn't exist."""
    kit_dir = tmp_path / "nonexistent-kit"
    # Note: NOT creating the directory

    kit_group = _load_single_kit_commands(
        kit_name="nonexistent-kit", kit_dir=kit_dir, manifest=valid_manifest, debug=False
    )

    assert kit_group is None


def test_lazy_loading_defers_import(tmp_path: Path, valid_manifest: KitManifest) -> None:
    """Test that lazy loading doesn't import commands until accessed."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()

    # Create the command file
    (commands_dir / "test_command.py").write_text(
        """import click

@click.command()
def test_command():
    '''Test command.'''
    click.echo('Hello')
""",
        encoding="utf-8",
    )

    kit_group = LazyKitGroup(
        kit_name="test-kit",
        kit_dir=kit_dir,
        manifest=valid_manifest,
        debug=False,
        name="test-kit",
        help="Test kit",
    )

    # Commands should not be loaded yet
    assert not kit_group._loaded

    # Create a mock context
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": False}

    # Access commands - this triggers loading
    kit_group.list_commands(ctx)

    # Now commands should be loaded
    assert kit_group._loaded


def test_debug_flag_shows_traceback(tmp_path: Path) -> None:
    """Test that debug mode shows full traceback on errors."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()

    # Create manifest with invalid command
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="INVALID",  # Invalid name
                path="commands/test.py",
                description="Test",
            )
        ],
    )

    kit_group = LazyKitGroup(
        kit_name="test-kit",
        kit_dir=kit_dir,
        manifest=manifest,
        debug=True,
        name="test-kit",
        help="Test kit",
    )

    ctx = click.Context(click.Command("test"))
    ctx.obj = {"debug": True}

    # In debug mode, validation errors should raise
    with pytest.raises(click.ClickException):
        kit_group._load_commands(ctx)


def test_path_construction_simple(tmp_path: Path) -> None:
    """Test path construction for simple single-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()

    (commands_dir / "simple.py").write_text(
        """import click

@click.command()
def simple():
    '''Simple command.'''
    pass
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(
                name="simple", path="commands/simple.py", description="Simple command"
            )
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None


def test_path_construction_nested(tmp_path: Path) -> None:
    """Test path construction for nested multi-level path."""
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()
    nested_dir = kit_dir / "a" / "b" / "c"
    nested_dir.mkdir(parents=True)

    (nested_dir / "nested.py").write_text(
        """import click

@click.command()
def nested():
    '''Nested command.'''
    pass
""",
        encoding="utf-8",
    )

    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
        commands=[
            CommandDefinition(name="nested", path="a/b/c/nested.py", description="Nested command")
        ],
    )

    kit_group = _load_single_kit_commands(
        kit_name="test-kit", kit_dir=kit_dir, manifest=manifest, debug=False
    )

    assert kit_group is not None
