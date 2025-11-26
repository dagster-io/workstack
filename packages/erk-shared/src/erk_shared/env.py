"""Environment detection utilities.

This module provides functions for detecting execution environment context,
such as whether the code is running in GitHub Actions CI.
"""

import os


def in_github_actions() -> bool:
    """Check if code is running in GitHub Actions CI.

    Returns:
        True if GITHUB_ACTIONS environment variable is set to "true",
        False otherwise.

    Example:
        >>> from erk_shared.env import in_github_actions
        >>> if in_github_actions():
        ...     # CI-specific behavior
        ...     pass
    """
    return os.environ.get("GITHUB_ACTIONS") == "true"
