"""Kit manifest models."""

import re
from dataclasses import dataclass, field

from dot_agent_kit.hooks.models import HookDefinition


@dataclass(frozen=True)
class KitCliCommandDefinition:
    """Kit cli command definition in kit manifest."""

    name: str
    path: str
    description: str

    def validate(self) -> list[str]:
        """Validate command definition fields.

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        # Validate name pattern: lowercase letters, numbers, hyphens only
        if not re.match(r"^[a-z][a-z0-9-]*$", self.name):
            errors.append(
                f"Name '{self.name}' must start with lowercase letter "
                "and contain only lowercase letters, numbers, and hyphens"
            )

        # Validate path ends with .py
        if not self.path.endswith(".py"):
            errors.append(f"Path '{self.path}' must end with .py")

        # Validate no directory traversal
        if ".." in self.path:
            errors.append(f"Path '{self.path}' cannot contain '..' (directory traversal)")

        # Validate path starts with kit_cli_commands/
        if not self.path.startswith("kit_cli_commands/"):
            errors.append(
                f"Path '{self.path}' must start with 'kit_cli_commands/' "
                "(kit CLI commands must be in kit_cli_commands directory)"
            )

        # Validate description is non-empty
        if not self.description or not self.description.strip():
            errors.append("Description cannot be empty")

        return errors


@dataclass(frozen=True)
class KitManifest:
    """Kit manifest from kit.yaml."""

    name: str
    version: str
    description: str
    artifacts: dict[str, list[str]]  # type -> paths
    license: str | None = None
    homepage: str | None = None
    hooks: list[HookDefinition] = field(default_factory=list)
    kit_cli_commands: list[KitCliCommandDefinition] = field(default_factory=list)

    def validate_namespace_pattern(self) -> list[str]:
        """Check if artifacts follow recommended hyphenated naming convention.

        This is informational only - the standard convention is:
        {type}s/{kit_name}-{suffix}/...

        For example: skills/devrun-make/SKILL.md for kit 'devrun'.

        Returns:
            List of warnings for artifacts that don't follow the convention (empty if all follow it)
        """
        # No enforcement - hyphenated naming is a convention, not a requirement
        return []
