import re
import tomllib
from pathlib import Path

import click

from workstack.cli.core import discover_repo_context, ensure_workstacks_dir
from workstack.core.context import WorkstackContext
from workstack.core.global_config_ops import GlobalConfigOps
from workstack.core.shell_ops import ShellOps


def detect_root_project_name(repo_root: Path) -> str | None:
    """Return the declared project name at the repo root, if any.

    Checks root `pyproject.toml`'s `[project].name`. If absent, tries to heuristically
    extract from `setup.py` by matching `name="..."` or `name='...'`.
    """

    root_pyproject = repo_root / "pyproject.toml"
    if root_pyproject.exists():
        data = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
        project = data.get("project") or {}
        name = project.get("name")
        if isinstance(name, str) and name:
            return name

    setup_py = repo_root / "setup.py"
    if setup_py.exists():
        text = setup_py.read_text(encoding="utf-8")
        m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
        if m:
            return m.group(1)

    return None


def is_repo_named(repo_root: Path, expected_name: str) -> bool:
    """Return True if the root project name matches `expected_name` (case-insensitive)."""
    name = detect_root_project_name(repo_root)
    return (name or "").lower() == expected_name.lower()


def detect_graphite(shell_ops: ShellOps) -> bool:
    """Detect if Graphite (gt) is installed and available in PATH."""
    return shell_ops.get_installed_tool_path("gt") is not None


def create_global_config(
    global_config_ops: GlobalConfigOps,
    shell_ops: ShellOps,
    workstacks_root: Path,
    shell_setup_complete: bool,
) -> None:
    """Create global config using the provided config ops."""
    use_graphite = detect_graphite(shell_ops)
    global_config_ops.set(
        workstacks_root=workstacks_root,
        use_graphite=use_graphite,
        shell_setup_complete=shell_setup_complete,
    )


def discover_presets() -> list[str]:
    """Discover available preset names by scanning the presets directory.

    Returns a list of preset names (without .toml extension).
    """
    presets_dir = Path(__file__).parent.parent / "presets"
    if not presets_dir.exists():
        return []

    return sorted(p.stem for p in presets_dir.glob("*.toml") if p.is_file())


def render_config_template(preset: str | None) -> str:
    """Return default config TOML content, optionally using a preset.

    If preset is None, uses the "generic" preset by default.
    Preset files are loaded from src/workstack/presets/<preset>.toml
    """
    preset_name = preset if preset is not None else "generic"
    presets_dir = Path(__file__).parent.parent / "presets"
    preset_file = presets_dir / f"{preset_name}.toml"

    if not preset_file.exists():
        raise ValueError(f"Preset '{preset_name}' not found at {preset_file}")

    return preset_file.read_text(encoding="utf-8")


def _add_gitignore_entry(content: str, entry: str, prompt_message: str) -> tuple[str, bool]:
    """Add an entry to gitignore content if not present and user confirms.

    Args:
        content: Current gitignore content
        entry: Entry to add (e.g., ".PLAN.md")
        prompt_message: Message to show user when confirming

    Returns:
        Tuple of (updated_content, was_modified)
    """
    # Entry already present
    if entry in content:
        return (content, False)

    # User declined
    if not click.confirm(prompt_message, default=True):
        return (content, False)

    # Ensure trailing newline before adding
    if not content.endswith("\n"):
        content += "\n"

    content += f"{entry}\n"
    return (content, True)


def get_shell_wrapper_content(shell: str) -> str:
    """Load the shell wrapper function for the given shell type."""
    shell_integration_dir = Path(__file__).parent.parent / "shell_integration"

    if shell == "fish":
        wrapper_file = shell_integration_dir / "fish_wrapper.fish"
    else:
        wrapper_file = shell_integration_dir / f"{shell}_wrapper.sh"

    if not wrapper_file.exists():
        raise ValueError(f"Shell wrapper not found for {shell}")

    return wrapper_file.read_text(encoding="utf-8")


def print_shell_setup_instructions(
    shell: str, rc_file: Path, completion_line: str, wrapper_content: str
) -> None:
    """Print formatted shell integration setup instructions for manual installation.

    Args:
        shell: The shell type (e.g., "zsh", "bash", "fish")
        rc_file: Path to the shell's rc file (e.g., ~/.zshrc)
        completion_line: The completion command to add (e.g., "source <(workstack completion zsh)")
        wrapper_content: The full wrapper function content to add
    """
    click.echo("\n" + "━" * 60)
    click.echo("Shell Integration Setup")
    click.echo("━" * 60)
    click.echo(f"\nDetected shell: {shell} ({rc_file})")
    click.echo("\nAdd the following to your rc file:\n")
    click.echo("# Workstack completion")
    click.echo(f"{completion_line}\n")
    click.echo("# Workstack shell integration")
    click.echo(wrapper_content)
    click.echo("\nThen reload your shell:")
    click.echo(f"  source {rc_file}")
    click.echo("━" * 60)


def perform_shell_setup(shell_ops: ShellOps) -> bool:
    """Print shell integration setup instructions for manual installation.

    Returns True if instructions were printed, False if setup was skipped.
    """
    shell_info = shell_ops.detect_shell()
    if not shell_info:
        click.echo("Unable to detect shell. Skipping shell integration setup.")
        return False

    shell, rc_file = shell_info

    # Resolve symlinks to show the real file path in instructions
    if rc_file.exists():
        rc_file = rc_file.resolve()

    click.echo(f"\nDetected shell: {shell}")
    click.echo("Shell integration provides:")
    click.echo("  - Tab completion for workstack commands")
    click.echo("  - Automatic worktree activation on 'workstack switch'")

    if not click.confirm("\nShow shell integration setup instructions?", default=True):
        click.echo("Skipping shell integration. You can run 'workstack init --shell' later.")
        return False

    # Generate the instructions
    completion_line = f"source <(workstack completion {shell})"
    wrapper_content = get_shell_wrapper_content(shell)

    # Print the formatted instructions
    print_shell_setup_instructions(shell, rc_file, completion_line, wrapper_content)

    return True


@click.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing repo config if present.")
@click.option(
    "--preset",
    type=str,
    default="auto",
    help=(
        "Config template to use. 'auto' detects preset based on repo characteristics. "
        f"Available: auto, {', '.join(discover_presets())}."
    ),
)
@click.option(
    "--list-presets",
    is_flag=True,
    help="List available presets and exit.",
)
@click.option(
    "--repo",
    is_flag=True,
    help="Initialize repository-level config only (skip global config setup).",
)
@click.option(
    "--shell",
    is_flag=True,
    help="Show shell integration setup instructions (completion + auto-activation wrapper).",
)
@click.pass_obj
def init_cmd(
    ctx: WorkstackContext, force: bool, preset: str, list_presets: bool, repo: bool, shell: bool
) -> None:
    """Initialize workstack for this repo and scaffold config.toml."""

    # Handle --shell flag: only do shell setup
    if shell:
        setup_complete = perform_shell_setup(ctx.shell_ops)
        if setup_complete:
            ctx.global_config_ops.set(shell_setup_complete=True)
        return

    # Discover available presets on demand
    available_presets = discover_presets()
    valid_choices = ["auto"] + available_presets

    # Handle --list-presets flag
    if list_presets:
        click.echo("Available presets:")
        for p in available_presets:
            click.echo(f"  - {p}")
        return

    # Validate preset choice
    if preset not in valid_choices:
        click.echo(f"Invalid preset '{preset}'. Available options: {', '.join(valid_choices)}")
        raise SystemExit(1)

    # Track if this is the first time init is run
    first_time_init = False

    # Check for global config first (unless --repo flag is set)
    if not repo and not ctx.global_config_ops.exists():
        first_time_init = True
        click.echo(f"Global config not found at {ctx.global_config_ops.get_path()}")
        click.echo("Please provide the path where you want to store all worktrees.")
        click.echo("(This directory will contain subdirectories for each repository)")
        workstacks_root = click.prompt("Worktrees root directory", type=Path)
        workstacks_root = workstacks_root.expanduser().resolve()
        create_global_config(
            ctx.global_config_ops, ctx.shell_ops, workstacks_root, shell_setup_complete=False
        )
        click.echo(f"Created global config at {ctx.global_config_ops.get_path()}")
        # Show graphite status on first init
        has_graphite = detect_graphite(ctx.shell_ops)
        if has_graphite:
            click.echo("Graphite (gt) detected - will use 'gt create' for new branches")
        else:
            click.echo("Graphite (gt) not detected - will use 'git' for branch creation")

    # When --repo is set, verify that global config exists
    if repo and not ctx.global_config_ops.exists():
        click.echo(f"Global config not found at {ctx.global_config_ops.get_path()}", err=True)
        click.echo("Run 'workstack init' without --repo to create global config first.", err=True)
        raise SystemExit(1)

    # Now proceed with repo-specific setup
    repo_context = discover_repo_context(ctx, ctx.cwd)

    # Determine config path based on --repo flag
    if repo:
        # Repository-level config goes in repo root
        cfg_path = repo_context.root / "config.toml"
    else:
        # Worktree-level config goes in workstacks_dir
        workstacks_dir = ensure_workstacks_dir(repo_context)
        cfg_path = workstacks_dir / "config.toml"

    if cfg_path.exists() and not force:
        click.echo(f"Config already exists: {cfg_path}. Use --force to overwrite.")
        raise SystemExit(1)

    effective_preset: str | None
    choice = preset.lower()
    if choice == "auto":
        effective_preset = "dagster" if is_repo_named(repo_context.root, "dagster") else "generic"
    else:
        effective_preset = choice

    content = render_config_template(effective_preset)
    cfg_path.write_text(content, encoding="utf-8")
    click.echo(f"Wrote {cfg_path}")

    # Check for .gitignore and add .PLAN.md and .env
    gitignore_path = repo_context.root / ".gitignore"
    if not gitignore_path.exists():
        # Early return: no gitignore file
        pass
    else:
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        modified = False

        # Add .PLAN.md
        gitignore_content, plan_added = _add_gitignore_entry(
            gitignore_content,
            ".PLAN.md",
            "Add .PLAN.md to .gitignore?",
        )
        modified = modified or plan_added

        # Add .env
        gitignore_content, env_added = _add_gitignore_entry(
            gitignore_content,
            ".env",
            "Add .env to .gitignore?",
        )
        modified = modified or env_added

        # Write if modified
        if modified:
            gitignore_path.write_text(gitignore_content, encoding="utf-8")
            click.echo(f"Updated {gitignore_path}")

    # On first-time init, offer shell setup if not already completed
    if first_time_init:
        if not ctx.global_config_ops.get_shell_setup_complete():
            setup_complete = perform_shell_setup(ctx.shell_ops)
            if setup_complete:
                ctx.global_config_ops.set(shell_setup_complete=True)
