import subprocess
from pathlib import Path

import click

from workstack.cli.config import LoadedConfig, load_config
from workstack.cli.core import discover_repo_context, ensure_workstacks_dir
from workstack.core.context import (
    WorkstackContext,
    read_trunk_from_pyproject,
    write_trunk_to_pyproject,
)


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


@click.group("config")
def config_group() -> None:
    """Manage workstack configuration."""


@config_group.command("list")
@click.pass_obj
def config_list(ctx: WorkstackContext) -> None:
    """Print a list of configuration keys and values."""
    # Try to load global config
    try:
        workstacks_root = ctx.global_config_ops.get_workstacks_root()
        use_graphite = ctx.global_config_ops.get_use_graphite()
        show_pr_info = ctx.global_config_ops.get_show_pr_info()
        show_pr_checks = ctx.global_config_ops.get_show_pr_checks()
        click.echo(click.style("Global configuration:", bold=True))
        click.echo(f"  workstacks_root={workstacks_root}")
        click.echo(f"  use_graphite={str(use_graphite).lower()}")
        click.echo(f"  show_pr_info={str(show_pr_info).lower()}")
        click.echo(f"  show_pr_checks={str(show_pr_checks).lower()}")
    except FileNotFoundError:
        click.echo(click.style("Global configuration:", bold=True))
        click.echo("  (not configured - run 'workstack init' to create)")

    # Try to load repo config
    try:
        repo = discover_repo_context(ctx, ctx.cwd)
        workstacks_dir = ensure_workstacks_dir(repo)
        cfg = load_config(workstacks_dir)
        trunk_branch = read_trunk_from_pyproject(repo.root)

        click.echo(click.style("\nRepository configuration:", bold=True))
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
    except Exception:
        click.echo(click.style("\nRepository configuration:", bold=True))
        click.echo("  (not in a git repository)")


@config_group.command("get")
@click.argument("key", metavar="KEY")
@click.pass_obj
def config_get(ctx: WorkstackContext, key: str) -> None:
    """Print the value of a given configuration key."""
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in ("workstacks_root", "use_graphite", "show_pr_info", "show_pr_checks"):
        try:
            if parts[0] == "workstacks_root":
                click.echo(str(ctx.global_config_ops.get_workstacks_root()))
            elif parts[0] == "use_graphite":
                click.echo(str(ctx.global_config_ops.get_use_graphite()).lower())
            elif parts[0] == "show_pr_info":
                click.echo(str(ctx.global_config_ops.get_show_pr_info()).lower())
            elif parts[0] == "show_pr_checks":
                click.echo(str(ctx.global_config_ops.get_show_pr_checks()).lower())
        except FileNotFoundError as e:
            click.echo(f"Global config not found at {ctx.global_config_ops.get_path()}", err=True)
            raise SystemExit(1) from e
        return

    # Handle repo config keys
    try:
        repo = discover_repo_context(ctx, ctx.cwd)
        workstacks_dir = ensure_workstacks_dir(repo)
        cfg = load_config(workstacks_dir)

        if parts[0] == "trunk-branch":
            trunk_branch = read_trunk_from_pyproject(repo.root)
            if trunk_branch:
                click.echo(trunk_branch)
            else:
                click.echo("not configured (will auto-detect)", err=True)
            return

        if parts[0] == "env":
            _get_env_value(cfg, parts, key)
            return

        if parts[0] == "post_create":
            _get_post_create_value(cfg, parts, key)
            return

        click.echo(f"Invalid key: {key}", err=True)
        raise SystemExit(1)

    except Exception as e:
        if "not in a git repository" in str(e).lower() or "not a git repository" in str(e).lower():
            click.echo("Not in a git repository", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


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
        if not ctx.global_config_ops.exists():
            click.echo(f"Global config not found at {ctx.global_config_ops.get_path()}", err=True)
            click.echo("Run 'workstack init' to create it.", err=True)
            raise SystemExit(1)

        # Update value using set()
        if parts[0] == "workstacks_root":
            ctx.global_config_ops.set(workstacks_root=Path(value).expanduser().resolve())
        elif parts[0] == "use_graphite":
            if value.lower() not in ("true", "false"):
                click.echo(f"Invalid boolean value: {value}", err=True)
                raise SystemExit(1)
            ctx.global_config_ops.set(use_graphite=value.lower() == "true")
        elif parts[0] == "show_pr_info":
            if value.lower() not in ("true", "false"):
                click.echo(f"Invalid boolean value: {value}", err=True)
                raise SystemExit(1)
            ctx.global_config_ops.set(show_pr_info=value.lower() == "true")
        elif parts[0] == "show_pr_checks":
            if value.lower() not in ("true", "false"):
                click.echo(f"Invalid boolean value: {value}", err=True)
                raise SystemExit(1)
            ctx.global_config_ops.set(show_pr_checks=value.lower() == "true")

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
