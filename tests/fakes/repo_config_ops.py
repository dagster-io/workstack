"""Fake repository config operations for testing.

FakeRepoConfigOps is an in-memory implementation that accepts pre-configured state
per repository in its constructor. All state is held in memory - no filesystem access.
"""

from dataclasses import replace
from pathlib import Path

from workstack.cli.config_schema import RepoConfig
from workstack.core.repo_config_ops import RepoConfigOps


class FakeRepoConfigOps(RepoConfigOps):
    """In-memory fake implementation - no filesystem access.

    All state is held in memory. Constructor accepts initial config per repository.
    This class has NO filesystem operations - all state is in-memory only.
    """

    def __init__(self, *, configs: dict[Path, RepoConfig] | None = None) -> None:
        """Create fake with optional pre-configured state per repository.

        Args:
            configs: Initial configuration state keyed by repo_root.
                    If None, empty dict is used (all repos return defaults).

        Example:
            # Config for specific repos
            >>> fake = FakeRepoConfigOps(
            ...     configs={
            ...         Path("/repo1"): RepoConfig(trunk_branch="main"),
            ...         Path("/repo2"): RepoConfig(trunk_branch="master"),
            ...     }
            ... )
            >>> fake.get_trunk_branch(Path("/repo1"))  # Returns "main"
            >>> fake.get_trunk_branch(Path("/repo2"))  # Returns "master"

            # Empty config (returns defaults for all repos)
            >>> fake = FakeRepoConfigOps()
            >>> fake.get_trunk_branch(Path("/any-repo"))  # Returns None (default)
        """
        self._configs = configs if configs is not None else {}

    def _get_config(self, repo_root: Path) -> RepoConfig:
        """Get config for repo, or return default if not set."""
        if repo_root in self._configs:
            return self._configs[repo_root]
        # Return default config if repo not configured
        return RepoConfig()

    def get_trunk_branch(self, repo_root: Path) -> str | None:
        config = self._get_config(repo_root)
        return config.trunk_branch

    def get_env(self, repo_root: Path) -> dict[str, str]:
        config = self._get_config(repo_root)
        return config.env

    def get_post_create_commands(self, repo_root: Path) -> list[str]:
        config = self._get_config(repo_root)
        return config.post_create_commands

    def get_post_create_shell(self, repo_root: Path) -> str | None:
        config = self._get_config(repo_root)
        return config.post_create_shell

    def get_full_config(self, repo_root: Path) -> RepoConfig:
        return self._get_config(repo_root)

    def set_trunk_branch(self, repo_root: Path, trunk_branch: str) -> None:
        """Set trunk branch in memory (no validation or filesystem)."""
        current = self._get_config(repo_root)
        self._configs[repo_root] = replace(current, trunk_branch=trunk_branch)

    def set_env(self, repo_root: Path, env: dict[str, str]) -> None:
        """Set environment variables in memory (no validation or filesystem)."""
        current = self._get_config(repo_root)
        self._configs[repo_root] = replace(current, env=env)

    def set_post_create_shell(self, repo_root: Path, shell: str | None) -> None:
        """Set post-create shell in memory (no validation or filesystem)."""
        current = self._get_config(repo_root)
        self._configs[repo_root] = replace(current, post_create_shell=shell)

    def add_post_create_command(self, repo_root: Path, command: str) -> None:
        """Add post-create command in memory (no validation or filesystem)."""
        current = self._get_config(repo_root)
        new_commands = list(current.post_create_commands) + [command]
        self._configs[repo_root] = replace(current, post_create_commands=new_commands)
