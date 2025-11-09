from dataclasses import replace
from pathlib import Path

import click

from workstack.cli.config import load_config, load_repo_config
from workstack.cli.core import discover_repo_context, ensure_workstacks_dir
from workstack.core.context import WorkstackContext, read_trunk_from_pyproject


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
    """Print the value of a given configuration key.

    Related Context:
    - Uses Python 3.10+ pattern matching for cleaner key dispatch
    - Each case handles one specific key pattern
    """
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

    # Handle repo config: load and extract with pattern matching
    repo = discover_repo_context(ctx, ctx.cwd)
    workstacks_dir = ensure_workstacks_dir(repo)
    config = load_repo_config(repo.root, workstacks_dir)

    match parts:
        case ["trunk-branch"]:
            if config.trunk_branch:
                click.echo(config.trunk_branch)
            else:
                click.echo("not configured (will auto-detect)", err=True)

        case ["env", subkey]:
            if subkey in config.env:
                click.echo(config.env[subkey])
            else:
                click.echo(f"Key not found: {key}", err=True)
                raise SystemExit(1)

        case ["post_create", "shell"]:
            if config.post_create_shell:
                click.echo(config.post_create_shell)
            else:
                click.echo(f"Key not found: {key}", err=True)
                raise SystemExit(1)

        case ["post_create", "commands"]:
            for cmd in config.post_create_commands:
                click.echo(cmd)

        case _:
            click.echo(f"Invalid key: {key}", err=True)
            raise SystemExit(1)


@config_group.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.pass_obj
def config_set(ctx: WorkstackContext, key: str, value: str) -> None:
    """Update configuration with a value for the given key.

    Related Context:
    - Simple pattern: load → modify → save (which validates)
    - Uses Python 3.10+ pattern matching for cleaner key dispatch
    - See Known Pitfalls: NO field-by-field validation
    """
    parts = key.split(".")

    # Handle global config keys (unchanged)
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

    # Handle repo config: load → modify → save (which validates)
    repo = discover_repo_context(ctx, Path.cwd())
    workstacks_dir = ensure_workstacks_dir(repo)
    config = load_repo_config(repo.root, workstacks_dir)

    # Use pattern matching to modify config based on key
    match parts:
        case ["trunk-branch"]:
            new_config = replace(config, trunk_branch=value)

        case ["env", env_key]:
            new_config = replace(config, env={**config.env, env_key: value})

        case ["post_create", "shell"]:
            new_config = replace(config, post_create_shell=value)

        case ["post_create", "commands"]:
            new_config = replace(config, post_create_commands=[*config.post_create_commands, value])

        case _:
            click.echo(f"Invalid key: {key}", err=True)
            raise SystemExit(1)

    # Save validates automatically - will exit if invalid
    from workstack.core.repo_config_ops import save_repo_config

    save_repo_config(repo.root, workstacks_dir, new_config, ctx.git_ops)
    click.echo(f"Set {key}={value}")
