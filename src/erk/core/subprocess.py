"""Subprocess execution with rich error context.

This module provides wrappers around subprocess.run that enrich CalledProcessError
exceptions with operation context, stderr output, and command details.

For integration layer subprocess calls, use run_subprocess_with_context().
For CLI-layer subprocess calls, use run_with_error_reporting() from erk.cli.subprocess_utils.
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Any


def run_subprocess_with_context(
    cmd: Sequence[str],
    operation_context: str,
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    encoding: str = "utf-8",
    check: bool = True,
    stdout: int | IO[Any] | None = None,
    stderr: int | IO[Any] | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Execute subprocess with enriched error reporting for integration layer.

    Wraps subprocess.run() to catch CalledProcessError and re-raise as RuntimeError
    with operation context, stderr output, and command details. This function is
    designed for use in integration layer code (e.g., RealGit, RealGitHub, RealGraphite).

    Args:
        cmd: Command and arguments to execute
        operation_context: Human-readable description of operation
            (e.g., "add worktree for branch feat-x")
        cwd: Working directory for command execution
        capture_output: Whether to capture stdout/stderr (default: True)
        text: Whether to decode output as text (default: True)
        encoding: Text encoding to use (default: "utf-8")
        check: Whether to raise on non-zero exit (default: True)
        stdout: File descriptor or file object for stdout
            (e.g., subprocess.PIPE, subprocess.DEVNULL, sys.stdout)
        stderr: File descriptor or file object for stderr
            (e.g., subprocess.PIPE, subprocess.DEVNULL, sys.stderr)
        **kwargs: Additional arguments passed to subprocess.run()

    Returns:
        CompletedProcess instance from subprocess.run()

    Raises:
        RuntimeError: When subprocess fails (check=True) with enriched context including:
            - Operation context
            - Command that was executed
            - Exit code
            - stderr output (if available)
        Original CalledProcessError is preserved via exception chaining

    Examples:
        >>> # Success case
        >>> result = run_subprocess_with_context(
        ...     ["git", "status"],
        ...     operation_context="check git status",
        ...     cwd=repo_root
        ... )
        >>> print(result.stdout)

        >>> # Failure case (raises RuntimeError with context)
        >>> try:
        ...     run_subprocess_with_context(
        ...         ["git", "checkout", "nonexistent"],
        ...         operation_context="checkout branch 'nonexistent'",
        ...         cwd=repo_root
        ...     )
        ... except RuntimeError as e:
        ...     print(e)  # "Failed to checkout branch 'nonexistent': ..."

    Notes:
        - This function is for integration layer code that needs exceptions with context
        - For CLI commands that need user-friendly output, use run_with_error_reporting() instead
        - Uses LBYL philosophy: caller should validate inputs before calling
        - Exception chaining preserves original CalledProcessError for debugging
        - Explicit stdout/stderr parameters disable capture_output to avoid ValueError
    """
    # Disable capture_output if explicit stdout or stderr provided
    # subprocess.run raises ValueError if capture_output conflicts with stdout/stderr
    if stdout is not None or stderr is not None:
        capture_output = False

    # Build subprocess.run kwargs, only adding stdout/stderr if explicitly provided
    run_kwargs: dict[str, Any] = {
        "cwd": cwd,
        "capture_output": capture_output,
        "text": text,
        "encoding": encoding,
        "check": check,
        **kwargs,
    }
    if stdout is not None:
        run_kwargs["stdout"] = stdout
    if stderr is not None:
        run_kwargs["stderr"] = stderr

    try:
        return subprocess.run(cmd, **run_kwargs)
    except subprocess.CalledProcessError as e:
        # Build rich error message with all available context
        error_parts = [f"Failed to {operation_context}"]

        # Add command details
        cmd_str = " ".join(str(arg) for arg in cmd)
        error_parts.append(f"Command: {cmd_str}")

        # Add exit code
        error_parts.append(f"Exit code: {e.returncode}")

        # Add stderr if available and non-empty
        if e.stderr:
            stderr_str = e.stderr.strip()
            if stderr_str:
                error_parts.append(f"stderr: {stderr_str}")

        # Combine all parts into detailed error message
        error_message = "\n".join(error_parts)

        # Re-raise as RuntimeError with exception chaining to preserve original
        raise RuntimeError(error_message) from e
