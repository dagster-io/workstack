"""Hook models for Claude Code hooks integration."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HookMetadata(BaseModel):
    """Metadata stored in settings.json _dot_agent field.

    This metadata allows us to track which kit installed which hook
    and manage hook lifecycle (removal, etc.).
    """

    model_config = ConfigDict(frozen=True)

    kit_id: str
    hook_id: str


class HookEntry(BaseModel):
    """Complete hook entry in settings.json.

    This represents the actual hook configuration that Claude Code reads.
    It combines the hook command with our tracking metadata.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str  # Always "command" for now
    command: str  # Full command to execute
    timeout: int
    metadata: HookMetadata = Field(alias="_dot_agent")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate hook type field."""
        if v not in ["command", "script"]:
            msg = f"Invalid hook type: {v}"
            raise ValueError(msg)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            msg = f"Timeout must be positive: {v}"
            raise ValueError(msg)
        return v

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to use by_alias=True by default for settings.json compatibility."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """Override to use by_alias=True by default for settings.json compatibility."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)


class HookDefinition(BaseModel):
    """Hook definition from kit.toml.

    This represents the hook configuration as defined in a kit's manifest.
    It contains all the information needed to install and manage a hook.
    """

    model_config = ConfigDict(frozen=True)

    hook_id: str
    lifecycle: str  # PreToolUse, PostToolUse, etc.
    matcher: str  # Tool name pattern (e.g., "Bash", "Write|Edit")
    script: str  # Relative path to hook script in kit
    description: str
    timeout: int = Field(default=30, gt=0)

    @field_validator("lifecycle")
    @classmethod
    def validate_lifecycle(cls, v: str) -> str:
        """Validate lifecycle is non-empty."""
        if not v.strip():
            msg = "Lifecycle cannot be empty"
            raise ValueError(msg)
        return v

    @field_validator("matcher")
    @classmethod
    def validate_matcher(cls, v: str) -> str:
        """Validate matcher is non-empty."""
        if not v.strip():
            msg = "Matcher cannot be empty"
            raise ValueError(msg)
        return v

    @field_validator("script")
    @classmethod
    def validate_script(cls, v: str) -> str:
        """Validate script path is non-empty."""
        if not v.strip():
            msg = "Script path cannot be empty"
            raise ValueError(msg)
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is non-empty."""
        if not v.strip():
            msg = "Description cannot be empty"
            raise ValueError(msg)
        return v
