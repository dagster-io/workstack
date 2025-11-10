import subprocess
from pathlib import Path

import click

from workstack.cli.config import LoadedConfig
from workstack.cli.core import discover_repo_context
from workstack.core.context import (
    GlobalConfigNotFound,
    WorkstackContext,
    read_trunk_from_pyproject,
    write_trunk_to_pyproject,
)
from workstack.core.global_config import GlobalConfig, global_config_path, save_global_config


def _get_env_value(cfg: LoadedConfig, parts: list[str], key: str) -> None:
    """Handle env.* configuration keys.

    Prints the value or exits with error if key not found.
    """
    if len(parts) != 2:
        click.echo(f"Invalid key: {key}", err=True)
        raise SystemExit(1)

    if parts[1] not in cfg.env:
        click.echo(f"Key not found: {key}", err=True)
        raise SystemExit(1)

    click.echo(cfg.env[parts[1]])


def _get_post_create_value(cfg: LoadedConfig, parts: list[str], key: str) -> None:
    """Handle post_create.* configuration keys.

    Prints the value or exits with error if key not found.
    """
    if len(parts) != 2:
        click.echo(f"Invalid key: {key}", err=True)
        raise SystemExit(1)

    # Handle shell subkey
    if parts[1] == "shell":
        if not cfg.post_create_shell:
            click.echo(f"Key not found: {key}", err=True)
            raise SystemExit(1)
        click.echo(cfg.post_create_shell)
        return

    # Handle commands subkey
    if parts[1] == "commands":
        for cmd in cfg.post_create_commands:
            click.echo(cmd)
        return

    # Unknown subkey
    click.echo(f"Key not found: {key}", err=True)
    raise SystemExit(1)


def _parse_boolean_value(value: str, field_name: str) -> bool:
    """Parse a boolean value from a string.

    Args:
        value: The string value to parse ("true" or "false", case-insensitive)
        field_name: The name of the field being set (for error messages)

    Returns:
        The parsed boolean value

    Raises:
        SystemExit: If the value is not "true" or "false"
    """
    if value.lower() not in ("true", "false"):
        click.echo(f"Invalid boolean value for {field_name}: {value}", err=True)
        raise SystemExit(1)
    return value.lower() == "true"


def _update_global_config_field(
    current_config: GlobalConfig,
    field_name: str,
    value: str,
) -> GlobalConfig:
    """Update a single field in GlobalConfig and return a new instance.

    Args:
        current_config: The current global configuration
        field_name: The field to update
        value: The new value as a string

    Returns:
        A new GlobalConfig instance with the updated field

    Raises:
        SystemExit: If the field name is invalid or value is invalid
    """
    match field_name:
        case "workstacks_root":
            return GlobalConfig(
                workstacks_root=Path(value).expanduser().resolve(),
                use_graphite=current_config.use_graphite,
                shell_setup_complete=current_config.shell_setup_complete,
                show_pr_info=current_config.show_pr_info,
                show_pr_checks=current_config.show_pr_checks,
            )
        case "use_graphite":
            return GlobalConfig(
                workstacks_root=current_config.workstacks_root,
                use_graphite=_parse_boolean_value(value, field_name),
                shell_setup_complete=current_config.shell_setup_complete,
                show_pr_info=current_config.show_pr_info,
                show_pr_checks=current_config.show_pr_checks,
            )
        case "show_pr_info":
            return GlobalConfig(
                workstacks_root=current_config.workstacks_root,
                use_graphite=current_config.use_graphite,
                shell_setup_complete=current_config.shell_setup_complete,
                show_pr_info=_parse_boolean_value(value, field_name),
                show_pr_checks=current_config.show_pr_checks,
            )
        case "show_pr_checks":
            return GlobalConfig(
                workstacks_root=current_config.workstacks_root,
                use_graphite=current_config.use_graphite,
                shell_setup_complete=current_config.shell_setup_complete,
                show_pr_info=current_config.show_pr_info,
                show_pr_checks=_parse_boolean_value(value, field_name),
            )
        case _:
            click.echo(f"Invalid global config field: {field_name}", err=True)
            raise SystemExit(1)


@click.group("config")
def config_group() -> None:
    """Manage workstack configuration."""


@config_group.command("list")
@click.pass_obj
def config_list(ctx: WorkstackContext) -> None:
    """Print a list of configuration keys and values."""
    # Display global config
    click.echo(click.style("Global configuration:", bold=True))
    if isinstance(ctx.global_config, GlobalConfigNotFound):
        click.echo("  (not configured - run 'workstack init' to create)")
    else:
        click.echo(f"  workstacks_root={ctx.global_config.workstacks_root}")
        click.echo(f"  use_graphite={str(ctx.global_config.use_graphite).lower()}")
        click.echo(f"  show_pr_info={str(ctx.global_config.show_pr_info).lower()}")
        click.echo(f"  show_pr_checks={str(ctx.global_config.show_pr_checks).lower()}")

    # Display repo config
    click.echo(click.style("\nRepository configuration:", bold=True))
    from workstack.core.repo_discovery import NoRepoSentinel

    if isinstance(ctx.repo, NoRepoSentinel):
        click.echo("  (not in a git repository)")
    else:
        trunk_branch = read_trunk_from_pyproject(ctx.repo.root)
        cfg = ctx.repo_config
        if trunk_branch:
            click.echo(f"  trunk-branch={trunk_branch}")
        if cfg.env:
            for key, value in cfg.env.items():
                click.echo(f"  env.{key}={value}")
        if cfg.post_create_shell:
            click.echo(f"  post_create.shell={cfg.post_create_shell}")
        if cfg.post_create_commands:
            click.echo(f"  post_create.commands={cfg.post_create_commands}")

        has_no_config = (
            not trunk_branch
            and not cfg.env
            and not cfg.post_create_shell
            and not cfg.post_create_commands
        )
        if has_no_config:
            click.echo("  (no configuration - run 'workstack init --repo' to create)")


@config_group.command("get")
@click.argument("key", metavar="KEY")
@click.pass_obj
def config_get(ctx: WorkstackContext, key: str) -> None:
    """Print the value of a given configuration key."""
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in ("workstacks_root", "use_graphite", "show_pr_info", "show_pr_checks"):
        if isinstance(ctx.global_config, GlobalConfigNotFound):
            config_path = global_config_path()
            click.echo(f"Global config not found at {config_path}", err=True)
            raise SystemExit(1)

        match parts[0]:
            case "workstacks_root":
                click.echo(str(ctx.global_config.workstacks_root))
            case "use_graphite":
                click.echo(str(ctx.global_config.use_graphite).lower())
            case "show_pr_info":
                click.echo(str(ctx.global_config.show_pr_info).lower())
            case "show_pr_checks":
                click.echo(str(ctx.global_config.show_pr_checks).lower())
        return

    # Handle repo config keys
    from workstack.core.repo_discovery import NoRepoSentinel

    if isinstance(ctx.repo, NoRepoSentinel):
        click.echo("Not in a git repository", err=True)
        raise SystemExit(1)

    if parts[0] == "trunk-branch":
        trunk_branch = read_trunk_from_pyproject(ctx.repo.root)
        if trunk_branch:
            click.echo(trunk_branch)
        else:
            click.echo("not configured (will auto-detect)", err=True)
        return

    cfg = ctx.repo_config

    match parts[0]:
        case "env":
            _get_env_value(cfg, parts, key)
        case "post_create":
            _get_post_create_value(cfg, parts, key)
        case _:
            click.echo(f"Invalid key: {key}", err=True)
            raise SystemExit(1)


@config_group.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.pass_obj
def config_set(ctx: WorkstackContext, key: str, value: str) -> None:
    """Update configuration with a value for the given key."""
    # Parse key into parts
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in ("workstacks_root", "use_graphite", "show_pr_info", "show_pr_checks"):
        if isinstance(ctx.global_config, GlobalConfigNotFound):
            config_path = global_config_path()
            click.echo(f"Global config not found at {config_path}", err=True)
            click.echo("Run 'workstack init' to create it.", err=True)
            raise SystemExit(1)

        # Create new config with updated value
        new_config = _update_global_config_field(ctx.global_config, parts[0], value)
        save_global_config(new_config)
        click.echo(f"Set {key}={value}")
        return

    # Handle repo config keys
    if parts[0] == "trunk-branch":
        # discover_repo_context checks for git repository and raises FileNotFoundError
        repo = discover_repo_context(ctx, Path.cwd())

        # Validate that the branch exists before writing
        result = subprocess.run(
            ["git", "rev-parse", "--verify", value],
            cwd=repo.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            click.echo(
                f"Error: Branch '{value}' does not exist in repository.\n"
                f"Create the branch first before configuring it as trunk.",
                err=True,
            )
            raise SystemExit(1)

        # Write configuration
        write_trunk_to_pyproject(repo.root, value)
        click.echo(f"Set trunk-branch={value}")
        return

    # Other repo config keys not implemented yet
    click.echo("Setting repo config keys not yet implemented", err=True)
    raise SystemExit(1)
