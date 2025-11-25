from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.dry_run import DryRunGraphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.parsing import (
    parse_graphite_cache,
    parse_graphite_pr_info,
    read_graphite_json_file,
)
from erk_shared.integrations.graphite.printing import PrintingGraphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

# Aliases for backward compatibility
GraphiteIntegration = Graphite
DryRunGraphiteIntegration = DryRunGraphite
FakeGraphiteIntegration = FakeGraphite
RealGraphiteIntegration = RealGraphite
StackPrinter = PrintingGraphite

# These functions don't exist yet - remove from exports for now
# parse_branch_list, parse_log_short_output, parse_stack_output, branch_to_stack_line

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
