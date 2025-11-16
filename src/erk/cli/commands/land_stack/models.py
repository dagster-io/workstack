"""Data models for land-stack command."""

from typing import NamedTuple


class BranchPR(NamedTuple):
    """Branch with associated PR information."""

    branch: str
    pr_number: int
    title: str
