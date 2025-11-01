"""Hook configuration models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HookConfig:
    """Single hook configuration from hooks.toml."""

    name: str
    lifecycle: str
    matcher: str
    script: str
    enabled: bool = True
    description: str | None = None

    def validate(self) -> list[str]:
        """Validate hook configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.name:
            errors.append("Hook name cannot be empty")

        if not self.lifecycle:
            errors.append("Hook lifecycle cannot be empty")

        valid_lifecycles = [
            "PreToolUse",
            "PostToolUse",
            "PreUserMessage",
            "PostUserMessage",
        ]
        if self.lifecycle not in valid_lifecycles:
            lifecycle_list = ", ".join(valid_lifecycles)
            errors.append(f"Invalid lifecycle '{self.lifecycle}'. Must be one of: {lifecycle_list}")

        if not self.script:
            errors.append("Hook script path cannot be empty")

        return errors


@dataclass(frozen=True)
class HookManifest:
    """Complete hook manifest from hooks.toml file."""

    kit_id: str
    kit_version: str
    hooks: list[HookConfig]

    def validate(self) -> list[str]:
        """Validate hook manifest.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.kit_id:
            errors.append("Kit ID cannot be empty")

        if not self.kit_version:
            errors.append("Kit version cannot be empty")

        # Validate each hook
        for i, hook in enumerate(self.hooks):
            hook_errors = hook.validate()
            for error in hook_errors:
                errors.append(f"Hook {i} ({hook.name}): {error}")

        # Check for duplicate hook names
        hook_names = [h.name for h in self.hooks]
        duplicates = {name for name in hook_names if hook_names.count(name) > 1}
        if duplicates:
            errors.append(f"Duplicate hook names: {', '.join(duplicates)}")

        return errors
