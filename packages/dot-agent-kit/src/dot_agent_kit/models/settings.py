"""Models for Claude Code settings.json structure."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatcherGroup(BaseModel):
    """A group of hooks that share the same matcher pattern.

    In settings.json, hooks are organized by lifecycle event and then
    grouped by matcher pattern. Each matcher group has a pattern and
    a list of hooks that should execute when a tool matching that
    pattern is used.
    """

    model_config = ConfigDict(frozen=True)

    matcher: str  # Tool name pattern (e.g., "Bash", "Write|Edit")
    hooks: list[dict[str, Any]]  # List of hook entries

    @field_validator("matcher")
    @classmethod
    def validate_matcher(cls, v: str) -> str:
        """Validate matcher is non-empty."""
        if not v.strip():
            msg = "matcher cannot be empty"
            raise ValueError(msg)
        return v

    @field_validator("hooks")
    @classmethod
    def validate_hooks(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate hooks is a list."""
        if not isinstance(v, list):
            msg = "hooks must be a list"
            raise ValueError(msg)
        return v


class ClaudeSettings(BaseModel):
    """Complete Claude Code settings.json structure.

    This represents the full settings.json file, including hooks
    and any other configuration Claude Code uses.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    hooks: dict[str, list[MatcherGroup]] = Field(default_factory=dict)

    @property
    def other(self) -> dict[str, Any]:
        """Get extra fields that are not hooks.

        This property provides backward compatibility for code that expects
        an 'other' dict field.
        """
        # Pydantic stores extra fields in __pydantic_extra__
        return dict(self.__pydantic_extra__ or {})

    def to_dict(self) -> dict[str, Any]:
        """Convert to settings.json format.

        This merges the hooks field with any extra fields that were preserved
        during parsing.
        """
        # Get all fields including extra fields
        result = self.model_dump()

        # Convert MatcherGroup objects to dicts for serialization
        if "hooks" in result and result["hooks"]:
            hooks_dict: dict[str, list[dict[str, Any]]] = {}
            for lifecycle, groups in self.hooks.items():
                hooks_dict[lifecycle] = [group.model_dump() for group in groups]
            result["hooks"] = hooks_dict

        return result

    @staticmethod
    def empty() -> "ClaudeSettings":
        """Create an empty settings object."""
        return ClaudeSettings(hooks={})
