"""Tests for context creation and regeneration."""

import os
from pathlib import Path

from workstack.core.context import create_context, regenerate_context


def test_regenerate_context_updates_cwd(tmp_path: Path) -> None:
    """Test that regenerate_context captures new cwd."""
    original_cwd = Path.cwd()

    try:
        # Create context in original directory
        ctx1 = create_context(dry_run=False)
        assert ctx1.cwd == original_cwd

        # Change directory
        os.chdir(tmp_path)

        # Regenerate context
        ctx2 = regenerate_context(ctx1)

        # Verify cwd updated
        assert ctx2.cwd == tmp_path
        assert ctx2.dry_run == ctx1.dry_run  # Preserved
    finally:
        # Cleanup
        os.chdir(original_cwd)


def test_regenerate_context_preserves_dry_run(tmp_path: Path) -> None:
    """Test that regenerate_context preserves dry_run flag."""
    ctx1 = create_context(dry_run=True)
    assert ctx1.dry_run is True

    ctx2 = regenerate_context(ctx1)
    assert ctx2.dry_run is True  # Preserved
