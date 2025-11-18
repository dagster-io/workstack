"""Forest data types for unified stack management."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Forest:
    """Named collection of worktrees belonging to the same Graphite stack.

    Forests are labels stored in metadata - renaming a forest NEVER moves
    worktrees or changes filesystem paths.
    """

    name: str
    worktrees: list[str]  # Worktree names (not paths)
    created_at: str  # ISO 8601 format
    root_branch: str  # Original trunk branch when created


@dataclass(frozen=True)
class ForestMetadata:
    """Container for all forests in a repository."""

    forests: dict[str, Forest]  # Map forest name → Forest


@dataclass(frozen=True)
class RerootState:
    """State for paused reroot operation.

    Persisted to ~/.erk/repos/<repo>/reroot-state.json when conflicts occur.
    """

    forest: str
    current_branch: str
    parent_branch: str
    parent_sha: str  # SHA of parent branch when conflict occurred
    remaining_branches: list[str]
    paused_on_conflicts: bool
    started_at: str  # ISO 8601 format
