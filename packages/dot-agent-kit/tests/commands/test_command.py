"""Tests for command discovery and name conversion."""

from pathlib import Path

from dot_agent_kit.commands.command import discover_commands


def test_discover_commands_empty_directory(tmp_project: Path) -> None:
    """Test discover_commands returns empty list when no commands exist."""
    # Create .claude/commands/ but leave it empty
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    result = discover_commands(tmp_project)

    assert result == []


def test_discover_commands_no_claude_directory(tmp_project: Path) -> None:
    """Test discover_commands returns empty list when .claude/ doesn't exist."""
    result = discover_commands(tmp_project)

    assert result == []


def test_discover_commands_flat_command(tmp_project: Path) -> None:
    """Test discover_commands converts flat command file correctly.

    File: .claude/commands/ensure-ci.md
    Expected: ensure-ci
    """
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create flat command file
    command_file = commands_dir / "ensure-ci.md"
    command_file.write_text("# Ensure CI", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["ensure-ci"]


def test_discover_commands_namespaced_command_single_level(tmp_project: Path) -> None:
    """Test discover_commands converts single-level namespaced command.

    File: .claude/commands/gt/submit-branch.md
    Expected: gt:submit-branch
    """
    commands_dir = tmp_project / ".claude" / "commands" / "gt"
    commands_dir.mkdir(parents=True)

    # Create namespaced command file
    command_file = commands_dir / "submit-branch.md"
    command_file.write_text("# Submit Branch", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["gt:submit-branch"]


def test_discover_commands_namespaced_command_multiple_levels(tmp_project: Path) -> None:
    """Test discover_commands converts multi-level namespaced command.

    File: .claude/commands/foo/bar/baz.md
    Expected: foo:bar:baz
    """
    commands_dir = tmp_project / ".claude" / "commands" / "foo" / "bar"
    commands_dir.mkdir(parents=True)

    # Create deeply nested command file
    command_file = commands_dir / "baz.md"
    command_file.write_text("# Baz Command", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["foo:bar:baz"]


def test_discover_commands_multiple_flat_commands(tmp_project: Path) -> None:
    """Test discover_commands finds and sorts multiple flat commands."""
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create multiple flat command files
    (commands_dir / "zebra.md").write_text("# Zebra", encoding="utf-8")
    (commands_dir / "alpha.md").write_text("# Alpha", encoding="utf-8")
    (commands_dir / "beta.md").write_text("# Beta", encoding="utf-8")

    result = discover_commands(tmp_project)

    # Should be sorted alphabetically
    assert result == ["alpha", "beta", "zebra"]


def test_discover_commands_mixed_flat_and_namespaced(tmp_project: Path) -> None:
    """Test discover_commands handles mix of flat and namespaced commands."""
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create flat command
    (commands_dir / "ensure-ci.md").write_text("# Ensure CI", encoding="utf-8")

    # Create namespaced commands
    gt_dir = commands_dir / "gt"
    gt_dir.mkdir()
    (gt_dir / "submit-branch.md").write_text("# Submit Branch", encoding="utf-8")
    (gt_dir / "update-pr.md").write_text("# Update PR", encoding="utf-8")

    erk_dir = commands_dir / "erk"
    erk_dir.mkdir()
    (erk_dir / "goto.md").write_text("# Goto", encoding="utf-8")

    result = discover_commands(tmp_project)

    # Should be sorted alphabetically
    assert result == [
        "ensure-ci",
        "erk:goto",
        "gt:submit-branch",
        "gt:update-pr",
    ]


def test_discover_commands_ignores_non_markdown_files(tmp_project: Path) -> None:
    """Test discover_commands ignores non-.md files."""
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create .md file (should be found)
    (commands_dir / "valid-command.md").write_text("# Valid", encoding="utf-8")

    # Create non-.md files (should be ignored)
    (commands_dir / "readme.txt").write_text("Readme", encoding="utf-8")
    (commands_dir / "config.json").write_text("{}", encoding="utf-8")
    (commands_dir / "script.py").write_text("print('hi')", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["valid-command"]


def test_discover_commands_handles_kebab_case_names(tmp_project: Path) -> None:
    """Test discover_commands preserves kebab-case in command names."""
    commands_dir = tmp_project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create commands with hyphens
    (commands_dir / "multi-word-command.md").write_text("# Multi Word", encoding="utf-8")
    (commands_dir / "another-long-name.md").write_text("# Another", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["another-long-name", "multi-word-command"]


def test_discover_commands_namespaced_with_kebab_case(tmp_project: Path) -> None:
    """Test discover_commands handles namespaced commands with kebab-case.

    File: .claude/commands/my-namespace/my-command.md
    Expected: my-namespace:my-command
    """
    commands_dir = tmp_project / ".claude" / "commands" / "my-namespace"
    commands_dir.mkdir(parents=True)

    command_file = commands_dir / "my-command.md"
    command_file.write_text("# My Command", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["my-namespace:my-command"]


def test_discover_commands_deeply_nested_with_multiple_separators(
    tmp_project: Path,
) -> None:
    """Test discover_commands converts deep nesting to colon-separated names.

    File: .claude/commands/level1/level2/level3/command.md
    Expected: level1:level2:level3:command
    """
    commands_dir = tmp_project / ".claude" / "commands" / "level1" / "level2" / "level3"
    commands_dir.mkdir(parents=True)

    command_file = commands_dir / "command.md"
    command_file.write_text("# Deep Command", encoding="utf-8")

    result = discover_commands(tmp_project)

    assert result == ["level1:level2:level3:command"]
