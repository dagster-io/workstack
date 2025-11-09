"""Branch metadata dataclass for Graphite integration."""

import secrets
from dataclasses import dataclass

# Sentinel for distinguishing "not provided" from "explicitly None"
_RANDOM_SHA = object()


@dataclass(frozen=True)
class BranchMetadata:
    """Metadata for a single gt-tracked branch.

    This is used by the gt commands to provide machine-readable branch information.
    """

    name: str
    parent: str | None
    children: list[str]
    is_trunk: bool
    commit_sha: str | None

    @staticmethod
    def main(
        name: str = "main",
        *,
        children: list[str] | None = None,
        sha: str | None | object = _RANDOM_SHA,
    ) -> "BranchMetadata":
        """Create trunk branch metadata for tests.

        Args:
            name: Branch name (default: "main")
            children: List of child branch names (default: [])
            sha: Commit SHA (default: random 6-char hex; pass None for unknown/missing SHA)

        Returns:
            BranchMetadata instance representing a trunk branch
        """
        # Generate random SHA if not provided, allow explicit None
        if sha is _RANDOM_SHA:
            actual_sha: str | None = secrets.token_hex(3)
        else:
            actual_sha = sha  # type: ignore[assignment]

        return BranchMetadata(
            name=name,
            parent=None,
            children=children if children is not None else [],
            is_trunk=True,
            commit_sha=actual_sha,
        )

    @staticmethod
    def branch(
        name: str,
        *,
        parent: str = "main",
        children: list[str] | None = None,
        sha: str | None | object = _RANDOM_SHA,
    ) -> "BranchMetadata":
        """Create feature branch metadata for tests.

        Args:
            name: Branch name (required)
            parent: Parent branch name (default: "main")
            children: List of child branch names (default: [])
            sha: Commit SHA (default: random 6-char hex; pass None for unknown/missing SHA)

        Returns:
            BranchMetadata instance representing a feature branch
        """
        # Generate random SHA if not provided, allow explicit None
        if sha is _RANDOM_SHA:
            actual_sha: str | None = secrets.token_hex(3)
        else:
            actual_sha = sha  # type: ignore[assignment]

        return BranchMetadata(
            name=name,
            parent=parent,
            children=children if children is not None else [],
            is_trunk=False,
            commit_sha=actual_sha,
        )
