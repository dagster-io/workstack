"""Shell detection and tool availability operations.

This module provides abstraction over shell-specific operations like detecting
the current shell and checking if command-line tools are installed. This abstraction
enables dependency injection for testing without mock.patch.
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path


def detect_shell_from_env(shell_env: str) -> tuple[str, Path] | None:
    """Detect shell type and config file from SHELL environment value.

    Args:
        shell_env: Value of SHELL environment variable (e.g., "/bin/zsh")

    Returns:
        Tuple of (shell_name, rc_file_path) or None if unsupported shell
    """
    if not shell_env:
        return None

    shell_name = Path(shell_env).name

    if shell_name == "bash":
        return ("bash", Path.home() / ".bashrc")
    if shell_name == "zsh":
        return ("zsh", Path.home() / ".zshrc")
    if shell_name == "fish":
        return ("fish", Path.home() / ".config" / "fish" / "config.fish")

    return None


def check_tool_in_path(tool_name: str) -> str | None:
    """Check if a tool exists in PATH.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Path to tool executable or None if not found
    """
    return shutil.which(tool_name)


class ShellOps(ABC):
    """Abstract interface for shell detection and tool availability checks.

    This abstraction enables testing without mock.patch by making shell
    operations injectable dependencies.
    """

    @abstractmethod
    def detect_shell(self) -> tuple[str, Path] | None:
        """Detect current shell and return configuration file path.

        Returns:
            Tuple of (shell_name, rc_file_path) or None if shell cannot be detected.

            Supported shells:
            - bash: returns ("bash", ~/.bashrc)
            - zsh: returns ("zsh", ~/.zshrc)
            - fish: returns ("fish", ~/.config/fish/config.fish)

        Example:
            >>> shell_ops = RealShellOps()
            >>> result = shell_ops.detect_shell()
            >>> if result:
            ...     shell_name, rc_file = result
            ...     print(f"Detected {shell_name} with rc file at {rc_file}")
        """
        ...

    @abstractmethod
    def check_tool_installed(self, tool_name: str) -> str | None:
        """Check if a command-line tool is installed and available in PATH.

        Args:
            tool_name: Name of the tool to check (e.g., "gt", "git", "python")

        Returns:
            Absolute path to the tool executable if found, None otherwise.

        Example:
            >>> shell_ops = RealShellOps()
            >>> gt_path = shell_ops.check_tool_installed("gt")
            >>> if gt_path:
            ...     print(f"Graphite found at {gt_path}")
        """
        ...


class RealShellOps(ShellOps):
    """Production implementation using system environment and PATH."""

    def detect_shell(self) -> tuple[str, Path] | None:
        """Detect current shell from SHELL environment variable.

        Implementation details:
        - Reads $SHELL environment variable
        - Extracts shell name from path (e.g., /bin/bash -> bash)
        - Maps to appropriate RC file location
        """
        shell_env = os.environ.get("SHELL", "")
        return detect_shell_from_env(shell_env)

    def check_tool_installed(self, tool_name: str) -> str | None:
        """Check if tool is in PATH using shutil.which."""
        return check_tool_in_path(tool_name)
