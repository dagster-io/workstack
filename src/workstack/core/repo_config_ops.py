"""Repository configuration operations.

This module provides validation and save operations for repository-level configuration.
"""

from pathlib import Path

import click

from workstack.cli.config_schema import RepoConfig
from workstack.core.git_ops import GitOps


def validate_repo_config(repo_root: Path, config: RepoConfig, git_ops: GitOps) -> None:
    """Validate entire repo config before saving.

    [CRITICAL: This is the ONLY place config validation should happen]

    Raises SystemExit if validation fails.

    Related Context:
    - Uses git_ops abstraction for branch validation (user preference)
    - Validates complete config atomically (see Complex Reasoning in .PLAN.md)
    """
    # Validate trunk_branch exists if set
    if config.trunk_branch is not None:
        # Use git_ops abstraction per user preference
        branch_head = git_ops.get_branch_head(repo_root, config.trunk_branch)
        if branch_head is None:
            click.echo(
                f"Error: Branch '{config.trunk_branch}' does not exist.\nCreate the branch first.",
                err=True,
            )
            raise SystemExit(1)

    # Validate post_create_shell exists if set
    if config.post_create_shell is not None:
        shell_path = Path(config.post_create_shell)
        if not shell_path.exists():
            click.echo(
                f"Error: Shell '{config.post_create_shell}' does not exist.",
                err=True,
            )
            raise SystemExit(1)


def save_repo_config(
    repo_root: Path, workstacks_dir: Path, config: RepoConfig, git_ops: GitOps
) -> None:
    """Validate and save entire repo config.

    [CRITICAL: Validation MUST pass before any files are written]

    Related Context:
    - Validates FIRST to prevent partial writes (see Architectural Insights in .PLAN.md)
    - Uses existing LoadedConfig and save helper (user preference)
    """
    # Validate FIRST - blocks save if invalid
    validate_repo_config(repo_root, config, git_ops)

    # Write trunk_branch to pyproject.toml
    if config.trunk_branch:
        from workstack.core.context import write_trunk_to_pyproject

        write_trunk_to_pyproject(repo_root, config.trunk_branch)

    # Write .workstack/config.toml using LoadedConfig
    from workstack.cli.config import LoadedConfig, save_config

    loaded = LoadedConfig(
        env=config.env,
        post_create_commands=config.post_create_commands,
        post_create_shell=config.post_create_shell,
    )
    save_config(workstacks_dir, loaded)
