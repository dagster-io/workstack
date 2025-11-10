"""Directory change utilities with automatic context regeneration.

Provides context manager for safely changing directories while ensuring
WorkstackContext remains synchronized with actual working directory.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from workstack.core.context import WorkstackContext, regenerate_context


@contextmanager
def change_directory(
    ctx: WorkstackContext, target_dir: Path, *, repo_root: Path
) -> Generator[WorkstackContext]:
    """Change directory and regenerate context automatically.

    This context manager handles directory changes safely by:
    1. Saving the original directory
    2. Changing to the target directory
    3. Regenerating context to capture new cwd
    4. Restoring original directory on exit (even if exception raised)

    Use this instead of manual os.chdir() + regenerate_context() pattern
    to prevent forgetting context regeneration and creating stale ctx.cwd bugs.

    Args:
        ctx: Current WorkstackContext
        target_dir: Directory to change to
        repo_root: Repository root for trunk_branch lookup during regeneration

    Yields:
        New WorkstackContext with updated cwd and trunk_branch

    Example:
        with change_directory(ctx, new_worktree_path, repo_root=repo.root) as ctx:
            # ctx.cwd is guaranteed to be new_worktree_path
            # Perform operations in new directory
            pass
        # Automatically restored to original directory
    """
    original_dir = Path.cwd()

    try:
        # Change to target directory
        os.chdir(target_dir)

        # Regenerate context with fresh cwd and trunk_branch
        new_ctx = regenerate_context(ctx, repo_root=repo_root)

        # Yield new context for use in with block
        yield new_ctx

    finally:
        # Always restore original directory, even if exception raised
        os.chdir(original_dir)
