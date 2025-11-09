"""Repository configuration operations interface and implementations."""

from abc import ABC, abstractmethod
from pathlib import Path

import click

from workstack.cli.config_schema import RepoConfig
from workstack.core.gitops import GitOps
from workstack.core.global_config_ops import GlobalConfigOps


class RepoConfigOps(ABC):
    """Abstract interface for repository configuration operations.

    All implementations (real and fake) must implement this interface.
    This interface provides direct access to config fields via getters and setters
    that validate atomically before saving.

    All methods take repo_root as first parameter since config varies by repository.
    """

    @abstractmethod
    def get_trunk_branch(self, repo_root: Path) -> str | None:
        """Get configured trunk branch for the repository.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Configured trunk branch name, or None if not configured
        """
        ...

    @abstractmethod
    def get_env(self, repo_root: Path) -> dict[str, str]:
        """Get environment variables for the repository.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Dictionary of environment variable names to values
        """
        ...

    @abstractmethod
    def get_post_create_commands(self, repo_root: Path) -> list[str]:
        """Get post-create commands for the repository.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            List of shell commands to run after worktree creation
        """
        ...

    @abstractmethod
    def get_post_create_shell(self, repo_root: Path) -> str | None:
        """Get post-create shell for the repository.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Path to shell executable, or None if not configured
        """
        ...

    @abstractmethod
    def get_full_config(self, repo_root: Path) -> RepoConfig:
        """Get complete repository configuration.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Complete RepoConfig object
        """
        ...

    @abstractmethod
    def set_trunk_branch(self, repo_root: Path, trunk_branch: str) -> None:
        """Set trunk branch for the repository.

        Validates configuration before saving.

        Args:
            repo_root: Path to the repository root directory
            trunk_branch: New trunk branch name

        Raises:
            SystemExit: If validation fails
        """
        ...

    @abstractmethod
    def set_env(self, repo_root: Path, env: dict[str, str]) -> None:
        """Set environment variables for the repository.

        Validates configuration before saving.

        Args:
            repo_root: Path to the repository root directory
            env: Dictionary of environment variable names to values

        Raises:
            SystemExit: If validation fails
        """
        ...

    @abstractmethod
    def set_post_create_shell(self, repo_root: Path, shell: str | None) -> None:
        """Set post-create shell for the repository.

        Validates configuration before saving.

        Args:
            repo_root: Path to the repository root directory
            shell: Path to shell executable, or None to unset

        Raises:
            SystemExit: If validation fails
        """
        ...

    @abstractmethod
    def add_post_create_command(self, repo_root: Path, command: str) -> None:
        """Add a post-create command for the repository.

        Validates configuration before saving.

        Args:
            repo_root: Path to the repository root directory
            command: Shell command to add

        Raises:
            SystemExit: If validation fails
        """
        ...


# ============================================================================
# Production Implementation
# ============================================================================


class RealRepoConfigOps(RepoConfigOps):
    """Production implementation with lazy loading and per-repo caching."""

    def __init__(self, global_config_ops: GlobalConfigOps, git_ops: GitOps) -> None:
        """Initialize with global config and git operations.

        Args:
            global_config_ops: Global config operations for getting workstacks root
            git_ops: Git operations abstraction for validation
        """
        self._global_config_ops = global_config_ops
        self._git_ops = git_ops
        self._cache: dict[Path, RepoConfig] = {}

    def _get_workstacks_dir(self, repo_root: Path) -> Path:
        """Get workstacks directory for a repository.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Path to .workstack directory for this repository
        """
        workstacks_root = self._global_config_ops.get_workstacks_root()
        repo_name = repo_root.name
        return workstacks_root / repo_name

    def _load_config(self, repo_root: Path) -> RepoConfig:
        """Load repo config from disk.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Complete RepoConfig object
        """
        from workstack.cli.config import load_repo_config

        workstacks_dir = self._get_workstacks_dir(repo_root)
        return load_repo_config(repo_root, workstacks_dir)

    def _ensure_cache(self, repo_root: Path) -> RepoConfig:
        """Ensure cache is loaded for the given repo and return it.

        Args:
            repo_root: Path to the repository root directory

        Returns:
            Cached RepoConfig for the repository
        """
        if repo_root not in self._cache:
            self._cache[repo_root] = self._load_config(repo_root)
        return self._cache[repo_root]

    def _invalidate_cache(self, repo_root: Path) -> None:
        """Invalidate cache for the given repo after writes.

        Args:
            repo_root: Path to the repository root directory
        """
        if repo_root in self._cache:
            del self._cache[repo_root]

    def _validate_config(self, repo_root: Path, config: RepoConfig) -> None:
        """Validate entire repo config before saving.

        [CRITICAL: This is the ONLY place config validation should happen]

        Args:
            repo_root: Path to the repository root directory
            config: Configuration to validate

        Raises:
            SystemExit: If validation fails
        """
        # Validate trunk_branch exists if set
        if config.trunk_branch is not None:
            branch_head = self._git_ops.get_branch_head(repo_root, config.trunk_branch)
            if branch_head is None:
                click.echo(
                    f"Error: Branch '{config.trunk_branch}' does not exist.\n"
                    f"Create the branch first.",
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

    def _save_config(self, repo_root: Path, config: RepoConfig) -> None:
        """Validate and save entire repo config.

        [CRITICAL: Validation MUST pass before any files are written]

        Args:
            repo_root: Path to the repository root directory
            config: Configuration to save

        Raises:
            SystemExit: If validation fails
        """
        # Validate FIRST - blocks save if invalid
        self._validate_config(repo_root, config)

        # Write trunk_branch to pyproject.toml
        if config.trunk_branch:
            from workstack.core.context import write_trunk_to_pyproject

            write_trunk_to_pyproject(repo_root, config.trunk_branch)

        # Write .workstack/config.toml using LoadedConfig
        from workstack.cli.config import LoadedConfig, save_config

        workstacks_dir = self._get_workstacks_dir(repo_root)
        loaded = LoadedConfig(
            env=config.env,
            post_create_commands=config.post_create_commands,
            post_create_shell=config.post_create_shell,
        )
        save_config(workstacks_dir, loaded)

        # Invalidate cache after write
        self._invalidate_cache(repo_root)

    def get_trunk_branch(self, repo_root: Path) -> str | None:
        config = self._ensure_cache(repo_root)
        return config.trunk_branch

    def get_env(self, repo_root: Path) -> dict[str, str]:
        config = self._ensure_cache(repo_root)
        return config.env

    def get_post_create_commands(self, repo_root: Path) -> list[str]:
        config = self._ensure_cache(repo_root)
        return config.post_create_commands

    def get_post_create_shell(self, repo_root: Path) -> str | None:
        config = self._ensure_cache(repo_root)
        return config.post_create_shell

    def get_full_config(self, repo_root: Path) -> RepoConfig:
        return self._ensure_cache(repo_root)

    def set_trunk_branch(self, repo_root: Path, trunk_branch: str) -> None:
        current = self._ensure_cache(repo_root)
        from dataclasses import replace

        new_config = replace(current, trunk_branch=trunk_branch)
        self._save_config(repo_root, new_config)

    def set_env(self, repo_root: Path, env: dict[str, str]) -> None:
        current = self._ensure_cache(repo_root)
        from dataclasses import replace

        new_config = replace(current, env=env)
        self._save_config(repo_root, new_config)

    def set_post_create_shell(self, repo_root: Path, shell: str | None) -> None:
        current = self._ensure_cache(repo_root)
        from dataclasses import replace

        new_config = replace(current, post_create_shell=shell)
        self._save_config(repo_root, new_config)

    def add_post_create_command(self, repo_root: Path, command: str) -> None:
        current = self._ensure_cache(repo_root)
        from dataclasses import replace

        new_commands = list(current.post_create_commands) + [command]
        new_config = replace(current, post_create_commands=new_commands)
        self._save_config(repo_root, new_config)


# ============================================================================
# Dry-Run Wrapper
# ============================================================================


class DryRunRepoConfigOps(RepoConfigOps):
    """Dry-run wrapper for repository config operations.

    Read operations are delegated to the wrapped implementation.
    Write operations print dry-run messages instead of modifying config files.
    """

    def __init__(self, wrapped: RepoConfigOps) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real repo config operations implementation to wrap
        """
        self._wrapped = wrapped

    def get_trunk_branch(self, repo_root: Path) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_trunk_branch(repo_root)

    def get_env(self, repo_root: Path) -> dict[str, str]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_env(repo_root)

    def get_post_create_commands(self, repo_root: Path) -> list[str]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_post_create_commands(repo_root)

    def get_post_create_shell(self, repo_root: Path) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_post_create_shell(repo_root)

    def get_full_config(self, repo_root: Path) -> RepoConfig:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_full_config(repo_root)

    def set_trunk_branch(self, repo_root: Path, trunk_branch: str) -> None:
        """Print dry-run message instead of updating config."""
        click.echo(
            f"[DRY RUN] Would set trunk_branch={trunk_branch} in {repo_root}",
            err=True,
        )

    def set_env(self, repo_root: Path, env: dict[str, str]) -> None:
        """Print dry-run message instead of updating config."""
        click.echo(
            f"[DRY RUN] Would set env={env} in {repo_root}",
            err=True,
        )

    def set_post_create_shell(self, repo_root: Path, shell: str | None) -> None:
        """Print dry-run message instead of updating config."""
        click.echo(
            f"[DRY RUN] Would set post_create_shell={shell} in {repo_root}",
            err=True,
        )

    def add_post_create_command(self, repo_root: Path, command: str) -> None:
        """Print dry-run message instead of updating config."""
        click.echo(
            f"[DRY RUN] Would add post_create_command={command} in {repo_root}",
            err=True,
        )
