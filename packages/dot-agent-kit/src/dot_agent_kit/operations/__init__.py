"""Operations for dot-agent-kit."""

from dot_agent_kit.operations.install import install_kit
from dot_agent_kit.operations.sync import (
    SyncResult,
    check_for_updates,
    sync_all_kits,
    sync_kit,
)
from dot_agent_kit.operations.user_install import (
    get_installation_context,
    install_kit_to_project,
)
from dot_agent_kit.operations.validation import (
    ValidationResult,
    validate_artifact,
    validate_project,
)

__all__ = [
    "get_installation_context",
    "install_kit",
    "install_kit_to_project",
    "SyncResult",
    "check_for_updates",
    "sync_all_kits",
    "sync_kit",
    "ValidationResult",
    "validate_artifact",
    "validate_project",
]
