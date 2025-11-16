"""Tests for completion command."""

from click.testing import CliRunner

from erk_dev.cli import cli


def test_completion_help() -> None:
    """Test completion help output shows all subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--help"])
    assert result.exit_code == 0
    assert "Generate shell completion scripts" in result.output
    assert "bash" in result.output
    assert "zsh" in result.output
    assert "fish" in result.output


def test_completion_bash_generates_script() -> None:
    """Test bash completion script generation."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0
    assert "_erk_dev_completion" in result.output
    assert "complete -o nosort -F _erk_dev_completion erk-dev" in result.output
    assert "bash" in result.output.lower()


def test_completion_zsh_generates_script() -> None:
    """Test zsh completion script generation."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0
    assert "#compdef erk-dev" in result.output
    assert "_erk_dev_completion" in result.output


def test_completion_fish_generates_script() -> None:
    """Test fish completion script generation."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code == 0
    assert "complete --no-files --command erk-dev" in result.output
    assert "erk-dev" in result.output


def test_completion_bash_help() -> None:
    """Test bash subcommand help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash", "--help"])
    assert result.exit_code == 0
    assert "Generate bash completion script" in result.output
    assert "source <(erk-dev completion bash)" in result.output


def test_completion_zsh_help() -> None:
    """Test zsh subcommand help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh", "--help"])
    assert result.exit_code == 0
    assert "Generate zsh completion script" in result.output
    assert "source <(erk-dev completion zsh)" in result.output


def test_completion_fish_help() -> None:
    """Test fish subcommand help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish", "--help"])
    assert result.exit_code == 0
    assert "Generate fish completion script" in result.output
    assert "erk-dev completion fish | source" in result.output
