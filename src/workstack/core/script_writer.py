"""Abstraction for activation script writing operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from workstack.cli.shell_utils import write_script_to_temp


@dataclass(frozen=True)
class ScriptResult:
    """Result of writing an activation script.

    Attributes:
        path: Path to the script file (may be sentinel in tests)
        content: Full content of the script including headers
    """

    path: Path
    content: str


class ScriptWriterOps(ABC):
    """Operations for writing shell activation scripts.

    This abstraction allows tests to verify script content without
    performing actual filesystem I/O.
    """

    @abstractmethod
    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write activation script and return path and content.

        Args:
            content: The shell script content (without metadata header)
            command_name: Command generating the script (e.g., 'jump', 'switch')
            comment: Description for the script header

        Returns:
            ScriptResult with path to script and full content
        """


class RealScriptWriterOps(ScriptWriterOps):
    """Production implementation that writes real temp files."""

    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write activation script to temp file.

        Args:
            content: The shell script content
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with path to created temp file and full content
        """
        script_path = write_script_to_temp(
            content,
            command_name=command_name,
            comment=comment,
        )

        # Read back the full content that was written (includes headers)
        full_content = script_path.read_text(encoding="utf-8")

        return ScriptResult(path=script_path, content=full_content)
