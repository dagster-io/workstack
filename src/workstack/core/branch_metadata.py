"""Branch metadata dataclass for Graphite integration."""

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class BranchMetadata:
    """Metadata for a single gt-tracked branch.

    This is used by the gt commands to provide machine-readable branch information.
    """

    name: str
    parent: str | None
    children: list[str]
    is_trunk: bool
    commit_sha: str

    @staticmethod
    def main(
        name: str = "main",
        *,
        children: list[str] | None = None,
        sha: str | None = None,
    ) -> "BranchMetadata":
        """Create trunk branch metadata for tests.

        Args:
            name: Branch name (default: "main")
            children: List of child branch names (default: [])
            sha: Commit SHA (default: random 6-char hex)

        Returns:
            BranchMetadata instance representing a trunk branch
        """
        return BranchMetadata(
            name=name,
            parent=None,
            children=children if children is not None else [],
            is_trunk=True,
            commit_sha=sha if sha is not None else secrets.token_hex(3),
        )

    @staticmethod
    def branch(
        name: str,
        *,
        parent: str = "main",
        children: list[str] | None = None,
        sha: str | None = None,
    ) -> "BranchMetadata":
        """Create feature branch metadata for tests.

        Args:
            name: Branch name (required)
            parent: Parent branch name (default: "main")
            children: List of child branch names (default: [])
            sha: Commit SHA (default: random 6-char hex)

        Returns:
            BranchMetadata instance representing a feature branch
        """
        return BranchMetadata(
            name=name,
            parent=parent,
            children=children if children is not None else [],
            is_trunk=False,
            commit_sha=sha if sha is not None else secrets.token_hex(3),
        )
