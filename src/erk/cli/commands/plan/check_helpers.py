"""Validation helper functions for plan checking.

These functions are pure business logic without CLI dependencies,
making them testable without Click framework overhead.
"""

from erk_shared.github.metadata import (
    PlanHeaderSchema,
    extract_plan_from_comment,
    find_metadata_block,
)


def validate_plan_header_exists(issue_body: str) -> tuple[bool, str]:
    """Check if plan-header metadata block exists in issue body.

    Args:
        issue_body: The body text of the GitHub issue

    Returns:
        Tuple of (passed, description) where:
        - passed: True if plan-header block exists, False otherwise
        - description: Human-readable validation result
    """
    plan_header_block = find_metadata_block(issue_body, "plan-header")
    if plan_header_block is None:
        return (False, "plan-header metadata block present")
    return (True, "plan-header metadata block present")


def validate_plan_header_schema(issue_body: str) -> tuple[bool, str]:
    """Validate plan-header has required fields and conforms to schema.

    Args:
        issue_body: The body text of the GitHub issue

    Returns:
        Tuple of (passed, description) where:
        - passed: True if plan-header validates, False otherwise
        - description: Human-readable validation result (includes error if failed)
    """
    plan_header_block = find_metadata_block(issue_body, "plan-header")
    if plan_header_block is None:
        return (False, "plan-header validation failed: metadata block not found")

    try:
        schema = PlanHeaderSchema()
        schema.validate(plan_header_block.data)
        return (True, "plan-header has required fields")
    except ValueError as e:
        # Extract first error message for cleaner output
        error_msg = str(e).split("\n")[0]
        return (False, f"plan-header validation failed: {error_msg}")


def validate_first_comment_exists(comments: list[str]) -> tuple[bool, str]:
    """Check if issue has at least one comment.

    Args:
        comments: List of comment bodies from the GitHub issue

    Returns:
        Tuple of (passed, description) where:
        - passed: True if at least one comment exists, False otherwise
        - description: Human-readable validation result
    """
    if not comments:
        return (False, "First comment exists")
    return (True, "First comment exists")


def validate_plan_body_extractable(first_comment: str) -> tuple[bool, str]:
    """Check if plan-body content can be extracted from first comment.

    Args:
        first_comment: Body text of the first GitHub issue comment

    Returns:
        Tuple of (passed, description) where:
        - passed: True if plan-body content is extractable, False otherwise
        - description: Human-readable validation result
    """
    plan_content = extract_plan_from_comment(first_comment)
    if plan_content is None:
        return (False, "plan-body content extractable")
    return (True, "plan-body content extractable")
