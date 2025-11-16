import click

from erk.cli.output import machine_output
from erk.core.context import WorkstackContext


@click.group("completion")
def completion_group() -> None:
    """Generate shell completion scripts."""


@completion_group.command("bash")
@click.pass_obj
def completion_bash(ctx: WorkstackContext) -> None:
    """Generate bash completion script.

    \b
    For automatic setup of both completion and auto-activation:
      workstack init --shell

    \b
    To load completions in your current shell session:
      source <(workstack completion bash)

    \b
    To load completions permanently, add to your ~/.bashrc:
      echo 'source <(workstack completion bash)' >> ~/.bashrc

    \b
    Alternatively, you can save the completion script to bash_completion.d:
      workstack completion bash > /usr/local/etc/bash_completion.d/workstack

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion_ops.generate_bash()
    machine_output(script, nl=False)


@completion_group.command("zsh")
@click.pass_obj
def completion_zsh(ctx: WorkstackContext) -> None:
    """Generate zsh completion script.

    \b
    For automatic setup of both completion and auto-activation:
      workstack init --shell

    \b
    To load completions in your current shell session:
      source <(workstack completion zsh)

    \b
    To load completions permanently, add to your ~/.zshrc:
      echo 'source <(workstack completion zsh)' >> ~/.zshrc

    \b
    Note: Make sure compinit is called in your ~/.zshrc after loading completions.

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion_ops.generate_zsh()
    machine_output(script, nl=False)


@completion_group.command("fish")
@click.pass_obj
def completion_fish(ctx: WorkstackContext) -> None:
    """Generate fish completion script.

    \b
    For automatic setup of both completion and auto-activation:
      workstack init --shell

    \b
    To load completions in your current shell session:
      workstack completion fish | source

    \b
    To load completions permanently:
      mkdir -p ~/.config/fish/completions && \\
      workstack completion fish > ~/.config/fish/completions/workstack.fish

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion_ops.generate_fish()
    machine_output(script, nl=False)
