"""Unit tests for plan check validation helpers."""

from erk_shared.github.metadata import MetadataBlock, render_metadata_block

from erk.cli.commands.plan.check_helpers import (
    validate_first_comment_exists,
    validate_plan_body_extractable,
    validate_plan_header_exists,
    validate_plan_header_schema,
)


def test_validate_plan_header_exists_with_valid_block() -> None:
    """Should pass when plan-header metadata block exists."""
    metadata = MetadataBlock("plan-header", {"objective": "test"})
    issue_body = render_metadata_block(metadata)

    passed, description = validate_plan_header_exists(issue_body)

    assert passed is True
    assert description == "plan-header metadata block present"


def test_validate_plan_header_exists_with_missing_block() -> None:
    """Should fail when plan-header metadata block is missing."""
    issue_body = "No metadata here"

    passed, description = validate_plan_header_exists(issue_body)

    assert passed is False
    assert description == "plan-header metadata block present"


def test_validate_plan_header_exists_with_different_block() -> None:
    """Should fail when only other metadata blocks exist."""
    metadata = MetadataBlock("other-block", {"data": "value"})
    issue_body = render_metadata_block(metadata)

    passed, description = validate_plan_header_exists(issue_body)

    assert passed is False
    assert description == "plan-header metadata block present"


def test_validate_plan_header_schema_with_valid_data() -> None:
    """Should pass when plan-header has all required fields."""
    metadata = MetadataBlock("plan-header", {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "testuser",
        "worktree_name": "test-worktree"
    })
    issue_body = render_metadata_block(metadata)

    passed, description = validate_plan_header_schema(issue_body)

    assert passed is True
    assert description == "plan-header has required fields"


def test_validate_plan_header_schema_with_missing_field() -> None:
    """Should fail when plan-header is missing required fields."""
    metadata = MetadataBlock("plan-header", {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z"
        # Missing created_by and worktree_name
    })
    issue_body = render_metadata_block(metadata)

    passed, description = validate_plan_header_schema(issue_body)

    assert passed is False
    assert "plan-header validation failed" in description


def test_validate_plan_header_schema_with_no_metadata() -> None:
    """Should fail when plan-header metadata block doesn't exist."""
    issue_body = "No metadata here"

    passed, description = validate_plan_header_schema(issue_body)

    assert passed is False
    assert description == "plan-header validation failed: metadata block not found"


def test_validate_first_comment_exists_with_comments() -> None:
    """Should pass when at least one comment exists."""
    comments = ["First comment", "Second comment"]

    passed, description = validate_first_comment_exists(comments)

    assert passed is True
    assert description == "First comment exists"


def test_validate_first_comment_exists_with_single_comment() -> None:
    """Should pass when exactly one comment exists."""
    comments = ["Only comment"]

    passed, description = validate_first_comment_exists(comments)

    assert passed is True
    assert description == "First comment exists"


def test_validate_first_comment_exists_with_no_comments() -> None:
    """Should fail when no comments exist."""
    comments: list[str] = []

    passed, description = validate_first_comment_exists(comments)

    assert passed is False
    assert description == "First comment exists"


def test_validate_plan_body_extractable_with_valid_plan() -> None:
    """Should pass when plan-body content is extractable."""
    metadata = MetadataBlock("plan-body", {})
    comment = render_metadata_block(metadata) + "\n\n# Plan Content\nSome plan details"

    passed, description = validate_plan_body_extractable(comment)

    assert passed is True
    assert description == "plan-body content extractable"


def test_validate_plan_body_extractable_with_no_plan_body() -> None:
    """Should fail when plan-body metadata block is missing."""
    comment = "Just a regular comment without plan-body"

    passed, description = validate_plan_body_extractable(comment)

    assert passed is False
    assert description == "plan-body content extractable"


def test_validate_plan_body_extractable_with_empty_comment() -> None:
    """Should fail when comment is empty."""
    comment = ""

    passed, description = validate_plan_body_extractable(comment)

    assert passed is False
    assert description == "plan-body content extractable"
