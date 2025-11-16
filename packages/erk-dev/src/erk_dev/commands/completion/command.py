"""Shell completion command for erk-dev."""

import os
import shutil
import subprocess
import sys

import click

from erk_dev.cli.output import machine_output, user_output


def erk_dev_command() -> list[str]:
    """Determine how to invoke erk-dev for completion generation."""
    executable = shutil.which("erk-dev")
    if executable is not None:
        return [executable]

    return [sys.executable, "-m", "erk_dev.__main__"]


def emit_completion_script(shell: str) -> None:
    """Generate and print the completion script for the requested shell."""
    env = os.environ.copy()
    env["_ERK_DEV_COMPLETE"] = f"{shell}_source"

    result = subprocess.run(
        erk_dev_command(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout:
        machine_output(result.stdout, nl=False)
    if result.stderr:
        user_output(result.stderr, nl=False)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


@click.group(name="completion")
def completion_command() -> None:
    """Generate shell completion scripts for erk-dev."""


@completion_command.command(name="bash")
def bash() -> None:
    r"""Generate bash completion script.

    \b
    Temporary (current session only):
        source <(erk-dev completion bash)

    Permanent installation:
        echo 'source <(erk-dev completion bash)' >> ~/.bashrc
        source ~/.bashrc

    Alternative - install to completion directory:
        erk-dev completion bash > ~/.local/share/bash-completion/completions/erk-dev
        # Then restart your shell
    """
    emit_completion_script("bash")


@completion_command.command(name="zsh")
def zsh() -> None:
    r"""Generate zsh completion script.

    \b
    Temporary (current session only):
        source <(erk-dev completion zsh)

    Permanent installation:
        echo 'source <(erk-dev completion zsh)' >> ~/.zshrc
        source ~/.zshrc

    Alternative - install to completion directory:
        mkdir -p ~/.zsh/completions
        erk-dev completion zsh > ~/.zsh/completions/_erk-dev
        # Add to ~/.zshrc: fpath=(~/.zsh/completions $fpath)
        # Then restart your shell
    """
    emit_completion_script("zsh")


@completion_command.command(name="fish")
def fish() -> None:
    r"""Generate fish completion script.

    \b
    Usage: erk-dev completion fish | source

    Permanent installation:
        mkdir -p ~/.config/fish/completions
        erk-dev completion fish > ~/.config/fish/completions/erk-dev.fish
        # Completions will be loaded automatically in new fish sessions
    """
    emit_completion_script("fish")
