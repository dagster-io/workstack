"""GitHub metadata blocks for embedding structured YAML data in markdown."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetadataBlock:
    """A metadata block with a key and structured YAML data."""

    key: str
    data: dict[str, Any]


class MetadataBlockSchema(ABC):
    """Base class for metadata block schemas."""

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> None:
        """Validate data against schema. Raises ValueError if invalid."""
        ...

    @abstractmethod
    def get_key(self) -> str:
        """Return the metadata block key this schema validates."""
        ...


@dataclass(frozen=True)
class ImplementationStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status blocks (completion status)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-implementation-status data structure."""
        required_fields = {
            "status",
            "completed_steps",
            "total_steps",
            "timestamp",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status values
        valid_statuses = {"pending", "in_progress", "complete", "failed"}
        if data["status"] not in valid_statuses:
            raise ValueError(
                f"Invalid status '{data['status']}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        # Validate numeric fields
        if not isinstance(data["completed_steps"], int):
            raise ValueError("completed_steps must be an integer")
        if not isinstance(data["total_steps"], int):
            raise ValueError("total_steps must be an integer")
        if data["completed_steps"] < 0:
            raise ValueError("completed_steps must be non-negative")
        if data["total_steps"] < 1:
            raise ValueError("total_steps must be at least 1")
        if data["completed_steps"] > data["total_steps"]:
            raise ValueError("completed_steps cannot exceed total_steps")

    def get_key(self) -> str:
        return "erk-implementation-status"


@dataclass(frozen=True)
class ProgressStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status progress blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate progress status data structure."""
        required_fields = {
            "status",
            "completed_steps",
            "total_steps",
            "timestamp",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status values
        valid_statuses = {"pending", "in_progress", "complete", "failed"}
        if data["status"] not in valid_statuses:
            raise ValueError(
                f"Invalid status '{data['status']}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        # Validate numeric fields
        if not isinstance(data["completed_steps"], int):
            raise ValueError("completed_steps must be an integer")
        if not isinstance(data["total_steps"], int):
            raise ValueError("total_steps must be an integer")
        if data["completed_steps"] < 0:
            raise ValueError("completed_steps must be non-negative")
        if data["total_steps"] < 1:
            raise ValueError("total_steps must be at least 1")
        if data["completed_steps"] > data["total_steps"]:
            raise ValueError("completed_steps cannot exceed total_steps")

        # step_description is optional - no validation needed if present

    def get_key(self) -> str:
        return "erk-implementation-status"


def create_metadata_block(
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema | None = None,
) -> MetadataBlock:
    """
    Create a metadata block with optional schema validation.

    Args:
        key: The metadata block key (appears in <code> tag)
        data: The structured data (will be rendered as YAML)
        schema: Optional schema to validate data against

    Returns:
        MetadataBlock instance

    Raises:
        ValueError: If schema validation fails
    """
    if schema is not None:
        schema.validate(data)

    return MetadataBlock(key=key, data=data)


def render_metadata_block(block: MetadataBlock) -> str:
    """
    Render a metadata block as markdown.

    Returns markdown like:
    <details>
    <summary><code>{key}</code></summary>
    ```yaml
    {yaml_content}
    ```
    </details>
    """
    yaml_content = yaml.safe_dump(
        block.data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Remove trailing newline from YAML dump
    yaml_content = yaml_content.rstrip("\n")

    return f"""<details>
<summary><code>{block.key}</code></summary>
```yaml
{yaml_content}
```
</details>"""


def create_implementation_status_block(
    status: str,
    completed_steps: int,
    total_steps: int,
    timestamp: str,
    summary: str | None = None,
) -> MetadataBlock:
    """Create an erk-implementation-status block with validation."""
    schema = ImplementationStatusSchema()
    data = {
        "status": status,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "timestamp": timestamp,
    }
    if summary is not None:
        data["summary"] = summary
    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def create_progress_status_block(
    status: str,
    completed_steps: int,
    total_steps: int,
    timestamp: str,
    step_description: str | None = None,
) -> MetadataBlock:
    """Create an erk-implementation-status progress block with validation."""
    schema = ProgressStatusSchema()
    data = {
        "status": status,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "timestamp": timestamp,
    }
    if step_description is not None:
        data["step_description"] = step_description
    return create_metadata_block(
        key=schema.get_key(),
        data=data,
        schema=schema,
    )


def parse_metadata_blocks(text: str) -> list[MetadataBlock]:
    """
    Extract all metadata blocks from markdown text.

    Args:
        text: Markdown text potentially containing metadata blocks

    Returns:
        List of parsed MetadataBlock instances
    """
    blocks: list[MetadataBlock] = []

    # Regex pattern to match metadata blocks
    pattern = (
        r"<details>\s*<summary><code>([^<]+)</code></summary>\s*"
        r"```yaml\s*(.*?)\s*```\s*</details>"
    )

    matches = re.finditer(pattern, text, re.DOTALL)

    for match in matches:
        key = match.group(1).strip()
        yaml_content = match.group(2)

        # Lenient parsing - return None on failure
        try:
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                logger.warning(f"Metadata block '{key}' YAML did not parse to dict, skipping")
                continue
            blocks.append(MetadataBlock(key=key, data=data))
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML for metadata block '{key}': {e}")
            continue

    return blocks


def find_metadata_block(text: str, key: str) -> MetadataBlock | None:
    """
    Find a specific metadata block by key.

    Args:
        text: Markdown text to search
        key: The metadata block key to find

    Returns:
        MetadataBlock if found, None otherwise
    """
    blocks = parse_metadata_blocks(text)
    for block in blocks:
        if block.key == key:
            return block
    return None


def extract_metadata_value(
    text: str,
    key: str,
    field: str,
) -> Any | None:
    """
    Extract a specific field value from a metadata block.

    Args:
        text: Markdown text to search
        key: The metadata block key
        field: The YAML field to extract

    Returns:
        The field value if found, None otherwise

    Example:
        >>> text = "...comment with metadata block..."
        >>> extract_metadata_value(text, "erk-implementation-status", "status")
        "complete"
    """
    block = find_metadata_block(text, key)
    if block is None:
        return None

    return block.data.get(field)
