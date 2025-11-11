"""Path utilities for tests.

This module provides utilities for working with paths in tests, particularly
sentinel paths that allow tests to avoid unnecessary filesystem dependencies.
"""

from pathlib import Path


def sentinel_path() -> Path:
    """Return sentinel path for tests that don't need real filesystem.

    Use this when testing pure logic (CLI exit codes, error messages, validation)
    that doesn't actually perform filesystem I/O. This eliminates the overhead
    of `isolated_filesystem()` and makes the test's intent clearer.

    Examples:
        # In any test that doesn't need real filesystem
        cwd = sentinel_path()
        repo_root = sentinel_path()

    Returns:
        Path object that can be used in WorkstackContext without filesystem access

    Note:
        - WorkstackContext.for_test() accepts any Path without validating existence
        - CliRunner.invoke() doesn't validate ctx.cwd exists
        - FakeGitOps is pure in-memory by default (no filesystem I/O)
        - All tests share the same sentinel path - tests are isolated via separate
          WorkstackContext instances, not different paths
    """
    return Path("/test/sentinel")
