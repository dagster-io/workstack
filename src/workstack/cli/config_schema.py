"""Configuration schema definitions.

This module defines the typed dataclasses representing workstack configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GlobalConfig:
    """Global user-level configuration.

    Stored in ~/.workstack/config.toml
    """

    workstacks_root: Path
    use_graphite: bool
    show_pr_info: bool
    show_pr_checks: bool


@dataclass(frozen=True)
class RepoConfig:
    """Repository-level configuration.

    Stored in:
    - trunk_branch: pyproject.toml [tool.workstack]
    - env, post_create_*: .workstack/config.toml
    """

    trunk_branch: str | None = None  # None = auto-detect
    env: dict[str, str] = field(default_factory=dict)
    post_create_commands: list[str] = field(default_factory=list)
    post_create_shell: str | None = None
