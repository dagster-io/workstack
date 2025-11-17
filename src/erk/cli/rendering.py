"""Output rendering framework for CLI commands.

Provides a common interface for rendering command output in different formats
(text, JSON). Commands that separate data collection from presentation can use
this framework to get JSON support automatically.
"""

from abc import ABC, abstractmethod
from typing import Any

from erk.cli.json_output import emit_json
from erk.cli.output import user_output


class OutputRenderer(ABC):
    """Base class for output renderers.

    Commands should define their output rendering through this interface.
    Different renderer implementations can then provide text, JSON, or other
    output formats automatically.
    """

    @abstractmethod
    def render_simple(self, data: dict[str, Any]) -> None:
        """Render simple key-value data.

        Used for commands with straightforward dictionary output.

        Args:
            data: Dictionary to render
        """
        pass

    @abstractmethod
    def render_list(self, data: dict[str, Any]) -> None:
        """Render worktree list data.

        Used for the list command and similar structured list output.

        Args:
            data: Dictionary with worktree list structure
        """
        pass

    @abstractmethod
    def render_status(self, status_data: Any) -> None:
        """Render status data.

        Used for the status command.

        Args:
            status_data: StatusData object or compatible structure
        """
        pass


class TextRenderer(OutputRenderer):
    """Renders output as formatted text for human consumption.

    Preserves existing text output behavior. Output goes to stderr via
    user_output() so it doesn't interfere with shell script data capture.
    """

    def render_simple(self, data: dict[str, Any]) -> None:
        """Render simple key-value pairs as text.

        Format: key: value (one per line)

        Args:
            data: Dictionary to render
        """
        for key, value in data.items():
            user_output(f"{key}: {value}")

    def render_list(self, data: dict[str, Any]) -> None:
        """Render list data as formatted text.

        This will be implemented when refactoring the list command.
        For now, commands using this should implement their own text output.

        Args:
            data: Dictionary with list structure
        """
        raise NotImplementedError(
            "TextRenderer.render_list() must be implemented during list command refactoring"
        )

    def render_status(self, status_data: Any) -> None:
        """Render status data using existing status renderer.

        Delegates to the SimpleRenderer from the status module to preserve
        existing text output behavior.

        Args:
            status_data: StatusData object
        """
        from erk.status.renderers.simple import SimpleRenderer

        SimpleRenderer().render(status_data)


class JsonRenderer(OutputRenderer):
    """Renders output as JSON for machine consumption.

    Output goes to stdout via machine_output() to enable shell pipelines.
    All data is serialized using the json_output helpers which handle
    Path, datetime, and dataclass conversions automatically.
    """

    def render_simple(self, data: dict[str, Any]) -> None:
        """Render simple data as JSON.

        Args:
            data: Dictionary to serialize as JSON
        """
        emit_json(data)

    def render_list(self, data: dict[str, Any]) -> None:
        """Render list data as JSON.

        Args:
            data: Dictionary with list structure to serialize as JSON
        """
        emit_json(data)

    def render_status(self, status_data: Any) -> None:
        """Render status data as JSON.

        Converts StatusData to validated Pydantic model, then converts to dict
        and emits as JSON.

        Args:
            status_data: StatusData object or compatible structure
        """
        from erk.cli.json_schemas import status_data_to_pydantic

        # Convert to Pydantic model for validation
        pydantic_model = status_data_to_pydantic(status_data)
        # Convert to dict (Pydantic handles Path/datetime serialization)
        dict_data = pydantic_model.model_dump(mode="json")
        emit_json(dict_data)


def get_renderer(format: str) -> OutputRenderer:
    """Factory function to get appropriate renderer based on format.

    Args:
        format: Output format ("text" or "json")

    Returns:
        Appropriate renderer instance

    Example:
        renderer = get_renderer(format)
        renderer.render_simple({"key": "value"})
    """
    if format == "json":
        return JsonRenderer()
    return TextRenderer()
