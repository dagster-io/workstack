"""Pydantic models for Claude Code hooks configuration."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HookMetadata(BaseModel):
    """Metadata tracking the kit and hook identity."""

    model_config = ConfigDict(frozen=True)

    kit_id: str = Field(..., min_length=1)
    hook_id: str = Field(..., min_length=1)


class HookEntry(BaseModel):
    """Represents a hook entry in settings.json."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    command: str = Field(..., min_length=1)
    timeout: int = Field(..., gt=0)
    dot_agent: HookMetadata = Field(..., alias="_dot_agent")


class MatcherGroup(BaseModel):
    """Groups hooks under a matcher pattern."""

    model_config = ConfigDict(frozen=True)

    matcher: str = Field(..., min_length=1)
    hooks: list[HookEntry]


class ClaudeSettings(BaseModel):
    """Top-level settings.json structure with hooks configuration.

    Uses extra="allow" to preserve unknown fields when reading and writing.
    """

    model_config = ConfigDict(extra="allow")

    permissions: dict[str, Any] | None = None
    hooks: dict[str, list[MatcherGroup]] | None = None


class HookDefinition(BaseModel):
    """Represents a hook definition in kit.toml manifest."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    lifecycle: str = Field(..., min_length=1)
    matcher: str = Field(..., min_length=1)
    script: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    timeout: int = Field(default=30, gt=0)

    @field_validator("lifecycle")
    @classmethod
    def validate_lifecycle(cls, v: str) -> str:
        """Validate lifecycle is non-empty string."""
        if not v or not v.strip():
            raise ValueError("lifecycle must be a non-empty string")
        return v

    @field_validator("matcher")
    @classmethod
    def validate_matcher(cls, v: str) -> str:
        """Validate matcher is non-empty string."""
        if not v or not v.strip():
            raise ValueError("matcher must be a non-empty string")
        return v

    @field_validator("script")
    @classmethod
    def validate_script(cls, v: str) -> str:
        """Validate script is non-empty string."""
        if not v or not v.strip():
            raise ValueError("script must be a non-empty string")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is non-empty string."""
        if not v or not v.strip():
            raise ValueError("description must be a non-empty string")
        return v
