"""Shared test utilities for land-stack tests.

This module contains common fixtures, helper functions, and test utilities
used across land-stack test modules.
"""

# Note: Currently all test utilities are encapsulated in the test files themselves
# or provided by the pure_workstack_env context manager.
#
# This file is a placeholder for future shared utilities if needed.
# Common patterns across tests:
# - pure_workstack_env(runner) for test environment setup
# - env.build_ops_from_branches() for Graphite/Git state construction
# - FakeGitHubOps with pr_statuses and pr_mergeability configuration
# - GlobalConfig with use_graphite=True for all land-stack tests
