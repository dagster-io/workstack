"""Shared utilities and interfaces for erk and dot-agent-kit."""

from erk_shared.github.issues import (
    DryRunGitHubIssues,
    FakeGitHubIssues,
    GitHubIssues,
    IssueInfo,
    RealGitHubIssues,
)
from erk_shared.github.metadata import (
    MetadataBlock,
    MetadataBlockSchema,
    create_implementation_status_block,
    create_metadata_block,
    create_plan_issue_block,
    create_progress_status_block,
    create_worktree_creation_block,
    render_erk_issue_event,
    render_metadata_block,
)
from erk_shared.impl_folder import (
    IssueReference,
    add_worktree_creation_comment,
    has_issue_reference,
    parse_progress_frontmatter,
    read_issue_reference,
    save_issue_reference,
)
from erk_shared.naming import (
    generate_filename_from_title,
    sanitize_worktree_name,
)

__version__ = "0.1.0"

__all__ = [
    # GitHub Issues Interface
    "GitHubIssues",
    "RealGitHubIssues",
    "FakeGitHubIssues",
    "DryRunGitHubIssues",
    "IssueInfo",
    # Naming Utilities
    "sanitize_worktree_name",
    "generate_filename_from_title",
    # Metadata Blocks
    "MetadataBlock",
    "MetadataBlockSchema",
    "create_metadata_block",
    "render_metadata_block",
    "render_erk_issue_event",
    "create_implementation_status_block",
    "create_progress_status_block",
    "create_worktree_creation_block",
    "create_plan_issue_block",
    # Impl Folder Utilities
    "parse_progress_frontmatter",
    "read_issue_reference",
    "save_issue_reference",
    "add_worktree_creation_comment",
    "has_issue_reference",
    "IssueReference",
]
