"""Plan issue utilities for wrapping plan content with git context metadata."""

from pathlib import Path

from erk.integrations.github.git_context import collect_plan_git_context
from erk.integrations.github.metadata_blocks import (
    create_plan_context_block,
    render_metadata_block,
)


def wrap_plan_with_context(plan_content: str, cwd: Path) -> str:
    """Wrap plan content with git context metadata block.

    Combines plan content with git context metadata block for complete
    issue body that tracks the state of the codebase at creation time.

    Args:
        plan_content: The plan markdown content
        cwd: Working directory to collect git context from

    Returns:
        Complete issue body with plan content followed by metadata block

    Raises:
        subprocess.CalledProcessError: If git operations fail
        ValueError: If in detached HEAD state or empty repo

    Note:
        Decision: This is a wrapper utility called by agents rather than
        CLI auto-injection. This provides more control and flexibility
        for different plan issue creation commands that may have varying
        requirements for metadata inclusion.
    """
    # Collect git context (may raise if git operations fail)
    git_context = collect_plan_git_context(cwd)

    # Create metadata block
    metadata_block = create_plan_context_block(git_context)

    # Render metadata block as markdown
    metadata_markdown = render_metadata_block(metadata_block)

    # Combine plan content first, then metadata at bottom
    return f"{plan_content}\n\n{metadata_markdown}"
