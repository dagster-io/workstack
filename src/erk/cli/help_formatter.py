"""Custom Click help formatter for organized command display."""

import click


class GroupedCommandGroup(click.Group):
    """Click Group that organizes commands into logical sections in help output.

    Commands are organized into sections based on their usage patterns:
    - Core Navigation: Primary workflow commands
    - Command Groups: Organized subcommands
    - Quick Access: Backward compatibility aliases
    """

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format commands into organized sections."""
        show_hidden = getattr(ctx, "show_hidden", False)

        commands = []
        hidden_commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if cmd.hidden:
                if show_hidden:
                    hidden_commands.append((subcommand, cmd))
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        # Define command organization
        core_navigation = ["checkout", "co", "up", "down"]
        command_groups = ["wt", "plan", "stack", "run", "admin", "config", "completion"]
        top_level_plans = ["list", "ls", "implement", "submit"]
        initialization = ["init"]

        # Categorize commands
        core_cmds = []
        group_cmds = []
        plan_cmds = []
        init_cmds = []
        alias_cmds = []

        for name, cmd in commands:
            if name in core_navigation:
                core_cmds.append((name, cmd))
            elif name in command_groups:
                group_cmds.append((name, cmd))
            elif name in top_level_plans:
                plan_cmds.append((name, cmd))
            elif name in initialization:
                init_cmds.append((name, cmd))
            else:
                # Everything else is a backward compatibility alias
                alias_cmds.append((name, cmd))

        # Format sections
        if plan_cmds:
            with formatter.section("Plans"):
                self._format_command_list(ctx, formatter, plan_cmds)

        if core_cmds:
            with formatter.section("Core Navigation"):
                self._format_command_list(ctx, formatter, core_cmds)

        if group_cmds:
            with formatter.section("Command Groups"):
                self._format_command_list(ctx, formatter, group_cmds)

        if alias_cmds:
            with formatter.section("Quick Access (Aliases)"):
                self._format_command_list(ctx, formatter, alias_cmds)

        if init_cmds:
            with formatter.section("Initialization"):
                self._format_command_list(ctx, formatter, init_cmds)

        if hidden_commands:
            with formatter.section("Deprecated (Hidden)"):
                self._format_command_list(ctx, formatter, hidden_commands)

    def _format_command_list(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
        commands: list[tuple[str, click.Command]],
    ) -> None:
        """Format a list of commands with their help text."""
        rows = []
        for name, cmd in commands:
            help_text = cmd.get_short_help_str(limit=formatter.width)
            rows.append((name, help_text))

        if rows:
            formatter.write_dl(rows)
