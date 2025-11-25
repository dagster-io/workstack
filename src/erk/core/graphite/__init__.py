"""High-level Graphite operations interface.

This module provides a clean abstraction over Graphite CLI (gt) calls.

NOTE: Implementation moved to erk_shared.integrations.graphite.
This module re-exports for backward compatibility.
"""

from erk_shared.integrations.graphite import (
    BranchMetadata,
    DryRunGraphite,
    DryRunGraphiteIntegration,
    FakeGraphite,
    FakeGraphiteIntegration,
    Graphite,
    GraphiteIntegration,
    PrintingGraphite,
    RealGraphite,
    RealGraphiteIntegration,
    StackPrinter,
    parse_graphite_cache,
    parse_graphite_pr_info,
    read_graphite_json_file,
)

__all__ = [
    "BranchMetadata",
    "DryRunGraphite",
    "DryRunGraphiteIntegration",
    "FakeGraphite",
    "FakeGraphiteIntegration",
    "Graphite",
    "GraphiteIntegration",
    "PrintingGraphite",
    "RealGraphite",
    "RealGraphiteIntegration",
    "StackPrinter",
    "parse_graphite_cache",
    "parse_graphite_pr_info",
    "read_graphite_json_file",
]
