"""Pure functions for plan manipulation and metadata.

This module re-exports from erk_shared.plan_utils for backwards compatibility.
New code should import directly from erk_shared.plan_utils.
"""

from erk_shared.plan_utils import extract_title_from_plan, format_error, wrap_plan_in_metadata_block

__all__ = ["extract_title_from_plan", "format_error", "wrap_plan_in_metadata_block"]
