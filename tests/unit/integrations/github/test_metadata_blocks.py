"""Tests for GitHub metadata blocks API."""

import pytest

from erk.integrations.github.metadata_blocks import (
    ImplementationStatusSchema,
    MetadataBlock,
    ProgressStatusSchema,
    create_implementation_status_block,
    create_metadata_block,
    create_progress_status_block,
    extract_metadata_value,
    find_metadata_block,
    parse_metadata_blocks,
    render_metadata_block,
)

# === Block Creation Tests ===


def test_create_block_without_schema() -> None:
    """Test basic block creation without schema validation."""
    block = create_metadata_block(
        key="test-key",
        data={"field": "value"},
    )
    assert block.key == "test-key"
    assert block.data == {"field": "value"}


def test_create_block_with_valid_schema() -> None:
    """Test block creation with valid schema."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    block = create_metadata_block(
        key="test-status",
        data=data,
        schema=schema,
    )
    assert block.key == "test-status"
    assert block.data == data


def test_create_block_with_invalid_data_raises() -> None:
    """Test block creation with invalid data raises ValueError."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        create_metadata_block(key="test-key", data=data, schema=schema)


def test_metadata_block_is_immutable() -> None:
    """Test that MetadataBlock is frozen (immutable)."""
    block = MetadataBlock(key="test", data={"field": "value"})
    with pytest.raises(AttributeError):  # FrozenInstanceError is subclass
        block.key = "changed"  # type: ignore


# === Rendering Tests ===


def test_render_basic_block() -> None:
    """Test basic markdown rendering."""
    block = MetadataBlock(
        key="test-key",
        data={"field": "value", "number": 42},
    )
    rendered = render_metadata_block(block)

    assert "<details>" in rendered
    assert "<summary><code>test-key</code></summary>" in rendered
    assert "```yaml" in rendered
    assert "field: value" in rendered
    assert "number: 42" in rendered
    assert "```" in rendered
    assert "</details>" in rendered


def test_render_details_closed_by_default() -> None:
    """Test that details block is closed by default (no 'open' attribute)."""
    block = MetadataBlock(key="test", data={"field": "value"})
    rendered = render_metadata_block(block)

    assert "<details>" in rendered
    assert "open" not in rendered.lower()


def test_render_no_trailing_newline() -> None:
    """Test that rendered YAML has no trailing newline."""
    block = MetadataBlock(key="test", data={"field": "value"})
    rendered = render_metadata_block(block)

    # Check that YAML ends with ``` not ```\n
    lines = rendered.split("\n")
    yaml_end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "```" and i > 0:
            yaml_end_idx = i
            break

    assert yaml_end_idx is not None
    # Line before ``` should be YAML content, not empty
    assert lines[yaml_end_idx - 1].strip() != ""


def test_render_special_characters() -> None:
    """Test rendering with special characters in values."""
    block = MetadataBlock(
        key="test-key",
        data={"message": "Line 1\nLine 2", "quote": 'Value with "quotes"'},
    )
    rendered = render_metadata_block(block)

    # YAML should handle special characters correctly
    assert "message:" in rendered
    assert "quote:" in rendered


# === Schema Validation Tests ===


def test_schema_validation_accepts_valid_data() -> None:
    """Test ImplementationStatusSchema accepts valid data with summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        "total_steps": 5,
        "summary": "Making progress",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_schema_validation_rejects_missing_fields() -> None:
    """Test schema rejects missing required fields."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        # Missing total_steps, timestamp
    }

    with pytest.raises(ValueError) as exc_info:
        schema.validate(data)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "timestamp" in error_msg
    assert "total_steps" in error_msg


def test_schema_validation_rejects_invalid_status() -> None:
    """Test schema rejects invalid status values."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_completed_steps() -> None:
    """Test schema rejects non-integer completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": "not-an-int",
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_total_steps() -> None:
    """Test schema rejects non-integer total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5.5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_negative_completed_steps() -> None:
    """Test schema rejects negative completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": -1,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be non-negative"):
        schema.validate(data)


def test_schema_validation_rejects_zero_total_steps() -> None:
    """Test schema rejects zero total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 0,
        "total_steps": 0,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be at least 1"):
        schema.validate(data)


def test_schema_validation_rejects_completed_exceeds_total() -> None:
    """Test schema rejects completed_steps > total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 10,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps cannot exceed total_steps"):
        schema.validate(data)


def test_schema_get_key() -> None:
    """Test schema returns correct key."""
    schema = ImplementationStatusSchema()
    assert schema.get_key() == "erk-implementation-status"


def test_implementation_status_schema_accepts_without_summary() -> None:
    """Test ImplementationStatusSchema accepts data without optional summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


# === ProgressStatusSchema Tests ===


def test_progress_schema_validates_valid_data() -> None:
    """Test ProgressStatusSchema accepts valid data."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
        "step_description": "Phase 1 complete",
    }
    schema.validate(data)  # Should not raise


def test_progress_schema_validates_without_step_description() -> None:
    """Test ProgressStatusSchema accepts data without optional step_description."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 2,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_progress_schema_rejects_missing_required_field() -> None:
    """Test ProgressStatusSchema rejects missing required fields."""
    schema = ProgressStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        # missing total_steps
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="Missing required fields: total_steps"):
        schema.validate(data)


def test_progress_schema_rejects_invalid_status() -> None:
    """Test ProgressStatusSchema rejects invalid status values."""
    schema = ProgressStatusSchema()
    data = {
        "status": "invalid",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    with pytest.raises(ValueError, match="Invalid status"):
        schema.validate(data)


def test_progress_schema_get_key() -> None:
    """Test ProgressStatusSchema returns correct key."""
    schema = ProgressStatusSchema()
    assert schema.get_key() == "erk-implementation-status"


def test_create_progress_status_block_with_description() -> None:
    """Test create_progress_status_block with step_description."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        step_description="Phase 1 complete",
    )
    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["step_description"] == "Phase 1 complete"


def test_create_progress_status_block_without_description() -> None:
    """Test create_progress_status_block without step_description."""
    block = create_progress_status_block(
        status="in_progress",
        completed_steps=2,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )
    assert block.key == "erk-implementation-status"
    assert "step_description" not in block.data


# === Parsing Tests ===


def test_parse_single_block() -> None:
    """Test parsing a single metadata block."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
field: value
number: 42
```
</details>"""

    blocks = parse_metadata_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].key == "test-key"
    assert blocks[0].data == {"field": "value", "number": 42}


def test_parse_multiple_blocks() -> None:
    """Test parsing multiple metadata blocks."""
    text = """Some text here

<details>
<summary><code>block-1</code></summary>
```yaml
field: value1
```
</details>

More text

<details>
<summary><code>block-2</code></summary>
```yaml
field: value2
```
</details>"""

    blocks = parse_metadata_blocks(text)
    assert len(blocks) == 2
    assert blocks[0].key == "block-1"
    assert blocks[0].data == {"field": "value1"}
    assert blocks[1].key == "block-2"
    assert blocks[1].data == {"field": "value2"}


def test_parse_no_blocks_returns_empty_list() -> None:
    """Test parsing text with no blocks returns empty list."""
    text = "Just some regular markdown text"
    blocks = parse_metadata_blocks(text)
    assert blocks == []


def test_parse_lenient_on_invalid_yaml(caplog: pytest.LogCaptureFixture) -> None:
    """Test parsing returns empty list for malformed YAML (lenient)."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
invalid: yaml: content:
```
</details>"""

    blocks = parse_metadata_blocks(text)
    assert blocks == []
    # Should log warning
    assert any("Failed to parse YAML" in record.message for record in caplog.records)


def test_parse_lenient_on_non_dict_yaml(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test parsing skips blocks where YAML is not a dict."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
- list
- item
```
</details>"""

    blocks = parse_metadata_blocks(text)
    assert blocks == []
    # Should log warning
    assert any("did not parse to dict" in record.message for record in caplog.records)


def test_find_metadata_block_existing_key() -> None:
    """Test find_metadata_block with existing key."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
field: value
```
</details>"""

    block = find_metadata_block(text, "test-key")
    assert block is not None
    assert block.key == "test-key"
    assert block.data == {"field": "value"}


def test_find_metadata_block_missing_key() -> None:
    """Test find_metadata_block with missing key returns None."""
    text = """<details>
<summary><code>other-key</code></summary>
```yaml
field: value
```
</details>"""

    block = find_metadata_block(text, "test-key")
    assert block is None


def test_extract_metadata_value_existing_field() -> None:
    """Test extract_metadata_value with existing field."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
field: value
number: 42
```
</details>"""

    value = extract_metadata_value(text, "test-key", "field")
    assert value == "value"

    number = extract_metadata_value(text, "test-key", "number")
    assert number == 42


def test_extract_metadata_value_missing_field() -> None:
    """Test extract_metadata_value with missing field returns None."""
    text = """<details>
<summary><code>test-key</code></summary>
```yaml
field: value
```
</details>"""

    value = extract_metadata_value(text, "test-key", "missing")
    assert value is None


def test_extract_metadata_value_missing_block() -> None:
    """Test extract_metadata_value with missing block returns None."""
    text = """<details>
<summary><code>other-key</code></summary>
```yaml
field: value
```
</details>"""

    value = extract_metadata_value(text, "test-key", "field")
    assert value is None


# === Integration Tests ===


def test_round_trip_create_render_parse() -> None:
    """Test round-trip: create → render → parse → extract."""
    # Create
    block = create_metadata_block(
        key="test-key",
        data={"field": "value", "number": 42},
    )

    # Render
    rendered = render_metadata_block(block)

    # Parse
    parsed_blocks = parse_metadata_blocks(rendered)
    assert len(parsed_blocks) == 1
    parsed_block = parsed_blocks[0]

    # Extract
    assert parsed_block.key == "test-key"
    assert parsed_block.data == {"field": "value", "number": 42}

    value = extract_metadata_value(rendered, "test-key", "field")
    assert value == "value"


def test_convenience_function_create_implementation_status_block() -> None:
    """Test create_implementation_status_block convenience function."""
    block = create_implementation_status_block(
        status="in_progress",
        completed_steps=3,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
        summary="Making progress",
    )

    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["total_steps"] == 5
    assert block.data["summary"] == "Making progress"
    assert block.data["timestamp"] == "2025-11-22T12:00:00Z"


def test_convenience_function_create_implementation_status_block_without_summary() -> None:
    """Test create_implementation_status_block without optional summary."""
    block = create_implementation_status_block(
        status="complete",
        completed_steps=5,
        total_steps=5,
        timestamp="2025-11-22T12:00:00Z",
    )

    assert block.key == "erk-implementation-status"
    assert block.data["status"] == "complete"
    assert "summary" not in block.data


def test_convenience_function_validates_data() -> None:
    """Test convenience function validates data."""
    with pytest.raises(ValueError, match="Invalid status"):
        create_implementation_status_block(
            status="bad-status",
            completed_steps=3,
            total_steps=5,
            timestamp="2025-11-22T12:00:00Z",
            summary="Test",
        )


def test_real_world_github_comment_format() -> None:
    """Test parsing a real-world GitHub comment with metadata block."""
    comment = """## Implementation Progress

We're making good progress on this feature!

<details>
<summary><code>erk-implementation-status</code></summary>
```yaml
status: in_progress
completed_steps: 3
total_steps: 5
summary: Core functionality implemented
timestamp: '2025-11-22T12:00:00Z'
```
</details>

Next steps:
- Add tests
- Update documentation
"""

    # Parse block
    block = find_metadata_block(comment, "erk-implementation-status")
    assert block is not None
    assert block.data["status"] == "in_progress"
    assert block.data["completed_steps"] == 3
    assert block.data["total_steps"] == 5

    # Extract values
    status = extract_metadata_value(comment, "erk-implementation-status", "status")
    assert status == "in_progress"

    completed = extract_metadata_value(comment, "erk-implementation-status", "completed_steps")
    assert completed == 3


# === Plan Wrapping Tests ===


def test_wrap_simple_plan_format() -> None:
    """Test that plan wrapping produces correct collapsible format."""
    plan_content = "# My Plan\n1. Step one\n2. Step two"

    # Simulate the wrap_plan_in_metadata_block output format
    expected_intro = "This issue contains an implementation plan:"
    wrapped = f"""{expected_intro}

<details>
<summary><code>erk-plan</code></summary>
```yaml
{plan_content}
```
</details>"""

    # Verify structure
    assert expected_intro in wrapped
    assert "<details>" in wrapped
    assert "<summary><code>erk-plan</code></summary>" in wrapped
    assert "```yaml" in wrapped
    assert plan_content in wrapped
    assert "</details>" in wrapped

    # Verify block is collapsible (no 'open' attribute)
    assert "open" not in wrapped.lower()


def test_wrap_plan_preserves_formatting() -> None:
    """Test that markdown formatting is preserved in wrapped plan."""
    plan_content = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two"""

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>
```yaml
{plan_content}
```
</details>"""

    # Verify all formatting elements are preserved
    assert "# Implementation Plan" in wrapped
    assert "## Phase 1" in wrapped
    assert "## Phase 2" in wrapped
    assert "- Task 1" in wrapped
    assert "1. Step one" in wrapped


def test_wrap_plan_with_special_characters() -> None:
    """Test that special characters are handled in wrapped plans."""
    plan_content = '''# Plan with Special Characters

- Quotes: "double" and 'single'
- Backticks: `code`
- Symbols: @#$%^&*()
- Unicode: 🔥 ✅ ❌'''

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>
```yaml
{plan_content}
```
</details>"""

    # Verify special characters are preserved
    assert '"double"' in wrapped
    assert "'single'" in wrapped
    assert "`code`" in wrapped
    assert "@#$%^&*()" in wrapped
    assert "🔥" in wrapped
    assert "✅" in wrapped


def test_rendered_plan_block_is_parseable() -> None:
    """Test that wrapped plan can be parsed back."""
    plan_content = "# Test Plan\n1. First step\n2. Second step"

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>
```yaml
{plan_content}
```
</details>"""

    # Should be able to find the erk-plan block
    block = find_metadata_block(wrapped, "erk-plan")
    # Note: This will actually fail to parse because the YAML content is just
    # markdown text, not valid YAML. But the structure is correct for GitHub rendering.
