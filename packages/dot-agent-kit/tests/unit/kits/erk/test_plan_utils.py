"""Unit tests for plan utility functions."""

from erk_shared.naming import generate_filename_from_title

from erk.data.kits.erk.plan_utils import extract_title_from_plan, wrap_plan_in_metadata_block


def test_wrap_plan_basic() -> None:
    """Test basic plan content is returned as-is (stripped).

    The function now returns plan content without metadata wrapping.
    Metadata blocks are added via separate GitHub comments.
    """
    plan = "## My Plan\n\n- Step 1\n- Step 2"
    result = wrap_plan_in_metadata_block(plan)

    # Should return plan content as-is (stripped)
    assert result == plan
    # Should NOT wrap in metadata block format
    assert "<details>" not in result
    assert "This issue contains an implementation plan:" not in result


def test_wrap_plan_strips_whitespace() -> None:
    """Test plan content strips leading/trailing whitespace."""
    plan = "\n\n  ## My Plan\n\n- Step 1\n- Step 2  \n\n"
    result = wrap_plan_in_metadata_block(plan)

    # Should strip whitespace from plan content
    assert result == "## My Plan\n\n- Step 1\n- Step 2"
    # Should NOT include metadata block structure
    assert "<details>" not in result
    assert "</details>" not in result


def test_extract_title_h1() -> None:
    """Test title extraction from H1 heading."""
    plan = "# Feature Name\n\nDetails..."
    assert extract_title_from_plan(plan) == "Feature Name"


def test_extract_title_h1_with_markdown() -> None:
    """Test title extraction removes markdown formatting."""
    plan = "# **Feature** `Name`\n\nDetails..."
    assert extract_title_from_plan(plan) == "Feature Name"


def test_extract_title_h2_fallback() -> None:
    """Test title extraction from H2 when no H1."""
    plan = "## My Feature\n\nDetails..."
    assert extract_title_from_plan(plan) == "My Feature"


def test_extract_title_first_line_fallback() -> None:
    """Test title extraction from first line when no headers."""
    plan = "Some plain text\n\nMore text..."
    assert extract_title_from_plan(plan) == "Some plain text"


def test_extract_title_skips_yaml_frontmatter() -> None:
    """Test title extraction skips YAML front matter delimiters."""
    plan = "---\ntitle: foo\n---\n# Real Title\n\nDetails..."
    assert extract_title_from_plan(plan) == "Real Title"


def test_extract_title_empty_plan() -> None:
    """Test title extraction from empty plan returns default."""
    assert extract_title_from_plan("") == "Implementation Plan"
    assert extract_title_from_plan("   \n\n  ") == "Implementation Plan"


def test_extract_title_truncates_long_titles() -> None:
    """Test title extraction truncates to 100 chars."""
    long_title = "A" * 150
    plan = f"# {long_title}\n\nDetails..."
    result = extract_title_from_plan(plan)
    assert len(result) == 100
    assert result == "A" * 100


def test_generate_filename_basic() -> None:
    """Test filename generation from simple title."""
    assert generate_filename_from_title("User Auth") == "user-auth-plan.md"


def test_generate_filename_special_chars() -> None:
    """Test filename generation removes special characters."""
    assert generate_filename_from_title("Fix: Database!!!") == "fix-database-plan.md"


def test_generate_filename_unicode() -> None:
    """Test filename generation handles unicode."""
    assert generate_filename_from_title("café Feature") == "cafe-feature-plan.md"


def test_generate_filename_emoji() -> None:
    """Test filename generation removes emojis."""
    assert generate_filename_from_title("🚀 Feature Launch 🎉") == "feature-launch-plan.md"


def test_generate_filename_collapse_hyphens() -> None:
    """Test filename generation collapses consecutive hyphens."""
    assert generate_filename_from_title("Fix:  Multiple   Spaces") == "fix-multiple-spaces-plan.md"


def test_generate_filename_empty_after_cleanup() -> None:
    """Test filename generation with only emoji returns default."""
    assert generate_filename_from_title("🚀🎉") == "plan.md"


def test_generate_filename_cjk() -> None:
    """Test filename generation removes CJK characters."""
    assert generate_filename_from_title("你好 Hello") == "hello-plan.md"


def test_generate_filename_strips_leading_trailing_hyphens() -> None:
    """Test filename generation strips edge hyphens."""
    assert generate_filename_from_title("-Feature Name-") == "feature-name-plan.md"
