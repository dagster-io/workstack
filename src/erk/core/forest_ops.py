"""Forest operations interface and implementations."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

import tomli
import tomli_w

from erk.core.forest_types import Forest as ForestData
from erk.core.forest_types import ForestMetadata, RerootState


class Forest(ABC):
    """Interface for forest metadata operations."""

    @abstractmethod
    def load_forests(self) -> ForestMetadata:
        """Load forest metadata from storage."""
        pass

    @abstractmethod
    def save_forests(self, metadata: ForestMetadata) -> None:
        """Save forest metadata to storage."""
        pass

    @abstractmethod
    def get_forest_for_worktree(self, worktree_name: str) -> ForestData | None:
        """Find forest containing given worktree."""
        pass

    @abstractmethod
    def load_reroot_state(self) -> RerootState | None:
        """Load reroot operation state if exists."""
        pass

    @abstractmethod
    def save_reroot_state(self, state: RerootState) -> None:
        """Save reroot operation state."""
        pass

    @abstractmethod
    def clear_reroot_state(self) -> None:
        """Remove reroot state file."""
        pass


class RealForest(Forest):
    """Real filesystem-based forest operations."""

    def __init__(self, repo_dir: Path) -> None:
        """Initialize with repository directory path."""
        self.repo_dir = repo_dir
        self.forests_path = repo_dir / "forests.toml"
        self.reroot_state_path = repo_dir / "reroot-state.json"

    def load_forests(self) -> ForestMetadata:
        """Load forest metadata from TOML file."""
        if not self.forests_path.exists():
            return ForestMetadata(forests={})

        with open(self.forests_path, "rb") as f:
            data = tomli.load(f)

        forests = {}
        for name, forest_data in data.get("forests", {}).items():
            forests[name] = ForestData(
                name=name,
                worktrees=forest_data["worktrees"],
                created_at=forest_data["created_at"],
                root_branch=forest_data["root_branch"],
            )

        return ForestMetadata(forests=forests)

    def save_forests(self, metadata: ForestMetadata) -> None:
        """Save forest metadata to TOML file."""
        data = {"forests": {}}

        for name, forest in metadata.forests.items():
            data["forests"][name] = {
                "worktrees": forest.worktrees,
                "created_at": forest.created_at,
                "root_branch": forest.root_branch,
            }

        # Ensure parent directory exists
        if not self.forests_path.parent.exists():
            self.forests_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.forests_path, "wb") as f:
            tomli_w.dump(data, f)

    def get_forest_for_worktree(self, worktree_name: str) -> ForestData | None:
        """Find forest containing given worktree."""
        metadata = self.load_forests()

        for forest in metadata.forests.values():
            if worktree_name in forest.worktrees:
                return forest

        return None

    def load_reroot_state(self) -> RerootState | None:
        """Load reroot state from JSON file."""
        if not self.reroot_state_path.exists():
            return None

        with open(self.reroot_state_path, encoding="utf-8") as f:
            data = json.load(f)

        return RerootState(
            forest=data["forest"],
            current_branch=data["current_branch"],
            parent_branch=data["parent_branch"],
            parent_sha=data["parent_sha"],
            remaining_branches=data["remaining_branches"],
            paused_on_conflicts=data["paused_on_conflicts"],
            started_at=data["started_at"],
        )

    def save_reroot_state(self, state: RerootState) -> None:
        """Save reroot state to JSON file."""
        data = {
            "forest": state.forest,
            "current_branch": state.current_branch,
            "parent_branch": state.parent_branch,
            "parent_sha": state.parent_sha,
            "remaining_branches": state.remaining_branches,
            "paused_on_conflicts": state.paused_on_conflicts,
            "started_at": state.started_at,
        }

        # Ensure parent directory exists
        if not self.reroot_state_path.parent.exists():
            self.reroot_state_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.reroot_state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def clear_reroot_state(self) -> None:
        """Remove reroot state file."""
        if self.reroot_state_path.exists():
            self.reroot_state_path.unlink()


class FakeForest(Forest):
    """In-memory forest operations for testing."""

    def __init__(self) -> None:
        """Initialize with empty in-memory storage."""
        self._forests = ForestMetadata(forests={})
        self._reroot_state: RerootState | None = None

    def load_forests(self) -> ForestMetadata:
        """Load forests from memory."""
        return self._forests

    def save_forests(self, metadata: ForestMetadata) -> None:
        """Save forests to memory."""
        self._forests = metadata

    def get_forest_for_worktree(self, worktree_name: str) -> ForestData | None:
        """Find forest containing given worktree."""
        for forest in self._forests.forests.values():
            if worktree_name in forest.worktrees:
                return forest

        return None

    def load_reroot_state(self) -> RerootState | None:
        """Load reroot state from memory."""
        return self._reroot_state

    def save_reroot_state(self, state: RerootState) -> None:
        """Save reroot state to memory."""
        self._reroot_state = state

    def clear_reroot_state(self) -> None:
        """Clear reroot state from memory."""
        self._reroot_state = None
