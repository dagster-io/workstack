"""Tests for CLI help formatter with alias display."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_help_shows_checkout_with_alias() -> None:
    """Help output shows 'checkout, co' on a single line."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show combined format: "checkout, co"
    assert "checkout, co" in result.output


def test_help_shows_list_with_alias() -> None:
    """Help output shows 'list, ls' on a single line."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show combined format: "list, ls"
    assert "list, ls" in result.output


def test_help_does_not_show_alias_as_separate_row() -> None:
    """Help output does not show 'co' or 'ls' as separate rows."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    output_lines = result.output.split("\n")

    # Check that 'co' and 'ls' don't appear as standalone commands
    # They should only appear as part of "checkout, co" and "list, ls"
    for line in output_lines:
        # Skip lines that are the combined format
        if "checkout, co" in line or "list, ls" in line:
            continue
        # Standalone alias would be at start of line with spaces
        stripped = line.strip()
        if stripped.startswith("co ") or stripped == "co":
            raise AssertionError(f"Found 'co' as standalone command: {line}")
        if stripped.startswith("ls ") or stripped == "ls":
            raise AssertionError(f"Found 'ls' as standalone command: {line}")


def test_aliases_still_work_as_commands() -> None:
    """Aliases like 'co' and 'ls' still work as invokable commands."""
    runner = CliRunner()

    # Test 'co --help' works (even though we can't invoke checkout without args)
    co_result = runner.invoke(cli, ["co", "--help"])
    assert co_result.exit_code == 0
    assert "checkout" in co_result.output.lower() or "worktree" in co_result.output.lower()

    # Test 'ls --help' works
    ls_result = runner.invoke(cli, ["ls", "--help"])
    assert ls_result.exit_code == 0
