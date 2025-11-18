"""Pure business logic functions for forest operations."""

import re
from datetime import UTC, datetime

from erk.core.forest_types import Forest, ForestMetadata


def create_forest(
    name: str,
    worktrees: list[str],
    root_branch: str,
    created_at: str | None = None,
) -> Forest:
    """Create new Forest instance with validation.

    Args:
        name: Forest name (must be valid)
        worktrees: List of worktree names
        root_branch: Trunk branch name
        created_at: ISO 8601 timestamp (defaults to now)

    Returns:
        New Forest instance

    Raises:
        ValueError: If name is invalid
    """
    if not validate_forest_name(name):
        raise ValueError(f"Invalid forest name: {name}")

    if created_at is None:
        created_at = datetime.now(UTC).isoformat()

    return Forest(
        name=name,
        worktrees=worktrees.copy(),
        created_at=created_at,
        root_branch=root_branch,
    )


def add_worktree_to_forest(forest: Forest, worktree_name: str) -> Forest:
    """Return new Forest with worktree added (immutable).

    Args:
        forest: Existing forest
        worktree_name: Name of worktree to add

    Returns:
        New Forest instance with updated worktrees
    """
    if worktree_name in forest.worktrees:
        return forest

    new_worktrees = forest.worktrees.copy()
    new_worktrees.append(worktree_name)

    return Forest(
        name=forest.name,
        worktrees=new_worktrees,
        created_at=forest.created_at,
        root_branch=forest.root_branch,
    )


def remove_worktree_from_forest(forest: Forest, worktree_name: str) -> Forest:
    """Return new Forest with worktree removed (immutable).

    Args:
        forest: Existing forest
        worktree_name: Name of worktree to remove

    Returns:
        New Forest instance with updated worktrees
    """
    if worktree_name not in forest.worktrees:
        return forest

    new_worktrees = [wt for wt in forest.worktrees if wt != worktree_name]

    return Forest(
        name=forest.name,
        worktrees=new_worktrees,
        created_at=forest.created_at,
        root_branch=forest.root_branch,
    )


def find_forest_by_worktree(metadata: ForestMetadata, worktree_name: str) -> Forest | None:
    """Search all forests for given worktree.

    Args:
        metadata: Forest metadata to search
        worktree_name: Name of worktree to find

    Returns:
        Forest containing worktree, or None if not found
    """
    for forest in metadata.forests.values():
        if worktree_name in forest.worktrees:
            return forest

    return None


def rename_forest(metadata: ForestMetadata, old_name: str, new_name: str) -> ForestMetadata:
    """Return new ForestMetadata with forest renamed.

    Args:
        metadata: Existing forest metadata
        old_name: Current forest name
        new_name: New forest name

    Returns:
        New ForestMetadata instance

    Raises:
        ValueError: If old_name doesn't exist or new_name conflicts
    """
    if old_name not in metadata.forests:
        raise ValueError(f"Forest '{old_name}' does not exist")

    if new_name in metadata.forests:
        raise ValueError(f"Forest '{new_name}' already exists")

    if not validate_forest_name(new_name):
        raise ValueError(f"Invalid forest name: {new_name}")

    new_forests = {}
    for name, forest in metadata.forests.items():
        if name == old_name:
            # Create new forest with new name
            new_forests[new_name] = Forest(
                name=new_name,
                worktrees=forest.worktrees,
                created_at=forest.created_at,
                root_branch=forest.root_branch,
            )
        else:
            new_forests[name] = forest

    return ForestMetadata(forests=new_forests)


def get_empty_forests(metadata: ForestMetadata, existing_worktrees: list[str]) -> list[str]:
    """Return forest names with zero worktrees.

    Args:
        metadata: Forest metadata to check
        existing_worktrees: List of currently existing worktree names

    Returns:
        List of forest names that have no existing worktrees
    """
    empty = []

    for name, forest in metadata.forests.items():
        # Check if any worktree in forest exists
        has_worktrees = any(wt in existing_worktrees for wt in forest.worktrees)
        if not has_worktrees:
            empty.append(name)

    return empty


def validate_forest_name(name: str) -> bool:
    """Check if forest name is valid.

    Forest names must be:
    - Non-empty
    - Max 30 characters
    - Alphanumeric + hyphens only

    Args:
        name: Forest name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    if len(name) > 30:
        return False

    # Must be alphanumeric + hyphens
    pattern = r"^[a-zA-Z0-9-]+$"
    if not re.match(pattern, name):
        return False

    return True
