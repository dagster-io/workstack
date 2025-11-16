"""Shell completion script generation operations.

This module provides abstraction over completion script generation for different
shells (bash, zsh, fish). This abstraction enables dependency injection for testing
without mock.patch.
"""

import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod


class CompletionOps(ABC):
    """Abstract interface for shell completion script generation.

    This abstraction enables testing without mock.patch by making completion
    operations injectable dependencies.
    """

    @abstractmethod
    def generate_bash(self) -> str:
        """Generate bash completion script.

        Returns:
            Bash completion script as a string.

        Example:
            >>> completion_ops = RealCompletionOps()
            >>> script = completion_ops.generate_bash()
            >>> print(script)  # Bash completion code
        """
        ...

    @abstractmethod
    def generate_zsh(self) -> str:
        """Generate zsh completion script.

        Returns:
            Zsh completion script as a string.

        Example:
            >>> completion_ops = RealCompletionOps()
            >>> script = completion_ops.generate_zsh()
            >>> print(script)  # Zsh completion code
        """
        ...

    @abstractmethod
    def generate_fish(self) -> str:
        """Generate fish completion script.

        Returns:
            Fish completion script as a string.

        Example:
            >>> completion_ops = RealCompletionOps()
            >>> script = completion_ops.generate_fish()
            >>> print(script)  # Fish completion code
        """
        ...

    @abstractmethod
    def get_erk_path(self) -> str:
        """Get path to erk executable.

        Returns:
            Absolute path to erk executable.

        Example:
            >>> completion_ops = RealCompletionOps()
            >>> path = completion_ops.get_erk_path()
            >>> print(path)  # e.g., "/usr/local/bin/erk"
        """
        ...


class RealCompletionOps(CompletionOps):
    """Production implementation using subprocess and Click's completion system."""

    def generate_bash(self) -> str:
        """Generate bash completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=bash_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "bash_source"
        result = subprocess.run([erk_exe], env=env, capture_output=True, text=True, check=True)
        return result.stdout

    def generate_zsh(self) -> str:
        """Generate zsh completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=zsh_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "zsh_source"
        result = subprocess.run([erk_exe], env=env, capture_output=True, text=True, check=True)
        return result.stdout

    def generate_fish(self) -> str:
        """Generate fish completion script via Click's completion system.

        Implementation details:
        - Uses _ERK_COMPLETE=fish_source environment variable
        - Invokes erk executable to generate completion code
        """
        erk_exe = self.get_erk_path()
        env = os.environ.copy()
        env["_ERK_COMPLETE"] = "fish_source"
        result = subprocess.run([erk_exe], env=env, capture_output=True, text=True, check=True)
        return result.stdout

    def get_erk_path(self) -> str:
        """Get erk executable path using shutil.which or sys.argv fallback."""
        erk_exe = shutil.which("erk")
        if not erk_exe:
            # Fallback to current Python + module
            erk_exe = sys.argv[0]
        return erk_exe
