"""JSON output utilities for CLI commands with machine-parseable output."""

import json
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from erk.cli.output import machine_output


class ErrorResponse(BaseModel):
    """Pydantic model for error JSON responses.

    Attributes:
        error: Error message
        error_type: Error class name (e.g., "ValueError")
        exit_code: Exit code for the process
    """

    model_config = ConfigDict(strict=True)

    error: str
    error_type: str
    exit_code: int = Field(default=1, ge=0, le=255)


def _serialize_for_json(obj: Any) -> Any:
    """Recursively serialize special types for JSON.

    Handles Path, datetime, and dataclass instances that appear in
    plain dict structures (not Pydantic models).

    For Pydantic models, use model.model_dump(mode='json') to convert
    to dict, then pass to emit_json().

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        dict_obj = asdict(obj)
        return _serialize_for_json(dict_obj)
    if isinstance(obj, dict):
        return {key: _serialize_for_json(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_serialize_for_json(item) for item in obj)
    return obj


def emit_json(data: dict[str, Any]) -> None:
    """Output JSON data to stdout for machine consumption.

    Routes JSON through machine_output() to ensure correct stream
    separation (data on stdout, human messages on stderr).

    Uses _serialize_for_json() to recursively handle special types:
    - Path objects → string representation
    - datetime objects → ISO format string
    - dataclass instances → dictionaries

    For Pydantic models, call model.model_dump(mode='json') before
    passing to this function.

    Args:
        data: Dictionary to serialize as JSON
    """
    serialized = _serialize_for_json(data)
    json_str = json.dumps(serialized, indent=2)
    machine_output(json_str)


def emit_json_error(error: str, error_type: str, exit_code: int = 1) -> None:
    """Output error as JSON and exit.

    Creates a validated ErrorResponse model (validates exit_code range),
    converts to dict, and emits as JSON.

    Args:
        error: Error message
        error_type: Error class name (e.g., "ValueError")
        exit_code: Exit code for the process (default: 1, must be 0-255)

    Raises:
        SystemExit: Always raises to terminate with specified exit code
    """
    error_response = ErrorResponse(
        error=error,
        error_type=error_type,
        exit_code=exit_code,
    )
    emit_json(error_response.model_dump(mode="json"))
    raise SystemExit(exit_code)


def json_error_boundary(func: Callable) -> Callable:
    """Decorator to catch exceptions and emit JSON errors when in JSON mode.

    Inspects function kwargs for 'format' parameter. If format == "json",
    catches exceptions and outputs structured JSON errors. Otherwise,
    lets exceptions bubble up for normal error handling.

    Example:
        @click.command()
        @click.option("--format", type=click.Choice(["text", "json"]), default="text")
        @json_error_boundary
        def my_command(format: str) -> None:
            # If error occurs and format == "json", outputs JSON error
            # Otherwise, raises exception normally
            ...

    Args:
        func: Command function to wrap

    Returns:
        Wrapped function with error boundary
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SystemExit:
            # Let SystemExit pass through unchanged
            raise
        except Exception as e:
            # Check if we're in JSON mode
            format_value = kwargs.get("format", "text")
            if format_value == "json":
                # Output JSON error and exit
                error_type = type(e).__name__
                error_message = str(e)
                emit_json_error(error_message, error_type, exit_code=1)
            else:
                # Re-raise for normal error handling
                raise

    return wrapper
