#!/usr/bin/env python3
"""
Workstack Local Standards Reminder Command

Outputs the workstack local coding standards reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run workstack-local-standards local-standards-reminder-hook.
"""

import click


@click.command()
def local_standards_reminder_hook() -> None:
    """Output workstack local standards reminder for UserPromptSubmit hook."""
    click.echo("<reminder>")
    click.echo(
        "🟡 WORKSTACK LOCAL STANDARDS: Load workstack-local-standards skill for "
        "project-specific conventions."
    )
    click.echo()
    click.echo("Key conventions:")
    click.echo("  • .claude/ artifacts: kebab-case (my-command.md, not my_command.md)")
    click.echo("  • Ops abstractions: Use ctx.git_ops, ctx.file_ops (not subprocess)")
    click.echo("  • Context regeneration: After os.chdir(), use regenerate_context()")
    click.echo("  • CLI tools: Use runner agent (not Bash) for make/pytest/ruff/gt")
    click.echo("  • Graphite stacks: upstack=away from main, downstack=toward main")
    click.echo("  • Test isolation: Use tmp_path or simulated_env (NEVER hardcoded paths)")
    click.echo("</reminder>")


if __name__ == "__main__":
    local_standards_reminder_hook()
