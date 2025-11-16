"""Path utilities for tests.

This module provides utilities for working with paths in tests, particularly
sentinel paths that allow tests to avoid unnecessary filesystem dependencies.
"""

from pathlib import Path


class SentinelPath(type(Path())):
    """Path subclass that throws on filesystem operations.

    This enforces that all filesystem checks go through fake operations
    (like FakeGitOps.path_exists()) rather than direct Path methods.
    This ensures high fidelity between test and production environments.

    File I/O operations (write_text/read_text) are tracked in memory,
    allowing tests to write and read files without touching the real filesystem.

    Raises:
        RuntimeError: If .exists() or other filesystem methods are called
    """

    # Class-level storage for file contents written via write_text()
    _file_storage: dict[str, str] = {}

    @classmethod
    def clear_file_storage(cls) -> None:
        """Clear all stored file contents.

        Useful for test isolation, though typically not needed since each test
        creates fresh sentinel paths with unique path strings.
        """
        cls._file_storage.clear()

    def exists(self) -> bool:
        """Throw error instead of checking filesystem.

        Production code should use FakeGitOps.path_exists() instead of
        directly calling Path.exists() in pure test mode.
        """
        raise RuntimeError(
            f"Called .exists() on sentinel path {self}. "
            "Production code must check paths through fake operations "
            "(e.g., git_ops.path_exists()) not direct filesystem calls. "
            "This ensures tests have high fidelity with production."
        )

    def resolve(self, strict: bool = False) -> "SentinelPath":
        """Return self without resolving (no-op for sentinel paths).

        In production, .resolve() canonicalizes paths and resolves symlinks.
        For sentinel paths, we just return self since there's no real filesystem.
        This allows production code to use .resolve() without modification.
        """
        return self

    def expanduser(self) -> "SentinelPath":
        """Expand ~ in path, returning SentinelPath to maintain sentinel behavior.

        In production, .expanduser() expands ~ to the home directory.
        For sentinel paths, we just return self since there's no real filesystem.
        This allows production code to use .expanduser() without modification,
        and ensures chained calls like .expanduser().resolve() stay in sentinel mode.
        """
        return self

    def is_dir(self) -> bool:
        """Throw error instead of checking directory."""
        raise RuntimeError(
            f"Called .is_dir() on sentinel path {self}. "
            "Use fake operations instead of filesystem checks."
        )

    def is_file(self) -> bool:
        """Throw error instead of checking file."""
        raise RuntimeError(
            f"Called .is_file() on sentinel path {self}. "
            "Use fake operations instead of filesystem checks."
        )

    @property
    def parent(self) -> Path:
        """Return parent as SentinelPath to prevent real filesystem operations.

        When mkdir(parents=True) is called, pathlib recursively calls .parent.mkdir().
        If .parent returns a regular Path, it tries to create real directories.
        By returning a SentinelPath, we keep all operations in sentinel mode.
        """
        parent_path = super().parent
        # Convert parent to SentinelPath to maintain sentinel behavior
        return SentinelPath(str(parent_path))

    def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        """No-op for sentinel paths (directories are assumed to exist).

        In production, .mkdir() creates actual directories on the filesystem.
        For sentinel paths, we skip this since there's no real filesystem.
        This allows production code to safely call .mkdir() without modification.
        """
        pass

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        """Store file content in memory for sentinel paths.

        In production, .write_text() writes content to the filesystem.
        For sentinel paths, we store in class-level dict for later retrieval.
        This allows tests to write files and read them back without real I/O.

        Returns the length of data to match Path.write_text() behavior.
        """
        # Store content keyed by path string
        SentinelPath._file_storage[str(self)] = data
        return len(data)

    def read_text(self, encoding: str | None = None, errors: str | None = None) -> str:
        """Retrieve file content from memory for sentinel paths.

        In production, .read_text() reads content from the filesystem.
        For sentinel paths, we retrieve from class-level storage.

        Raises:
            FileNotFoundError: If file was never written via write_text()
        """
        path_str = str(self)
        if path_str not in SentinelPath._file_storage:
            raise FileNotFoundError(f"No content stored for sentinel path {self}")
        return SentinelPath._file_storage[path_str]


def sentinel_path(path: str = "/test/sentinel") -> Path:
    """Return sentinel path for tests that don't need real filesystem.

    Use this when testing pure logic (CLI exit codes, error messages, validation)
    that doesn't actually perform filesystem I/O. This eliminates the overhead
    of `isolated_filesystem()` and makes the test's intent clearer.

    The returned SentinelPath throws errors if filesystem operations are attempted,
    enforcing that all checks go through fake operations for high test fidelity.

    Args:
        path: The sentinel path string (default: "/test/sentinel")

    Examples:
        # In any test that doesn't need real filesystem
        cwd = sentinel_path()
        repo_root = sentinel_path("/test/repo")

    Returns:
        SentinelPath that throws on filesystem operations

    Note:
        - ErkContext.for_test() accepts any Path without validating existence
        - CliRunner.invoke() doesn't validate ctx.cwd exists
        - FakeGitOps should provide path_exists() for path checks
        - All tests share the same sentinel path - tests are isolated via separate
          ErkContext instances, not different paths
    """
    return SentinelPath(path)
