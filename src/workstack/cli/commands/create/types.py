"""Data structures for the create command subpackage.

This module contains all the strongly-typed data structures used across
the create command implementation. These structures enable clean data flow
between modules and eliminate the need for passing many individual parameters.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CreateVariant = Literal["from_current_branch", "from_branch", "plan", "with_dot_plan", "regular"]


@dataclass(frozen=True)
class WorktreeTarget:
    """Where and how to create the worktree."""

    name: str
    path: Path
    repo_root: Path
    workstacks_dir: Path


@dataclass(frozen=True)
class BranchConfig:
    """Git branching configuration."""

    branch: str | None
    ref: str | None
    use_existing_branch: bool
    use_graphite: bool


@dataclass(frozen=True)
class PlanConfig:
    """Plan file handling configuration."""

    source_file: Path | None
    keep_source: bool
    destination: Path | None = None


@dataclass(frozen=True)
class DotPlanSource:
    """Source workstack for copying .plan/ folder."""

    name: str
    path: Path
    branch: str
    parent_branch: str


@dataclass(frozen=True)
class OutputConfig:
    """How to output results."""

    mode: Literal["script", "json", "human"]
    stay: bool


@dataclass(frozen=True)
class CreationRequest:
    """Complete creation request after parsing and validation.

    This is the central data structure that flows through the system.
    The orchestrator builds it from CLI arguments after validation,
    and each variant handler receives it as their primary input.

    Attributes:
        variant: Which creation variant to execute
        target: Where to create the worktree
        branch_override: Explicit branch name if provided via --branch
        ref: Git ref to base the worktree on
        plan_config: Plan file configuration (for plan variant)
        dot_plan_source: Source workstack info (for with_dot_plan variant)
        output: How to format and display results
        no_post: Whether to skip post-create commands
    """

    variant: CreateVariant
    target: WorktreeTarget
    branch_override: str | None
    ref: str | None
    plan_config: PlanConfig | None
    dot_plan_source: DotPlanSource | None
    output: OutputConfig
    no_post: bool


@dataclass(frozen=True)
class CreationResult:
    """Result of a variant creation operation.

    Each variant returns this structure with the relevant fields populated.
    Not all fields are used by all variants.

    Attributes:
        branch_config: The branch configuration that was used
        plan_dest: Path to the plan destination (for plan variant)
        source_name: Name of source workstack (for with_dot_plan variant)
    """

    branch_config: BranchConfig
    plan_dest: Path | None = None
    source_name: str | None = None
