from datetime import datetime
from pathlib import Path

import pytest

from workstack.cli.commands.create import (
    default_branch_for_worktree,
    ensure_unique_worktree_name,
    extract_trailing_number,
    sanitize_branch_component,
    sanitize_worktree_name,
    strip_plan_from_filename,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Foo", "foo"),
        (" Foo Bar ", "foo-bar"),
        ("A/B C", "a/b-c"),
        ("@@weird!!name??", "weird-name"),
        # Test truncation to 30 characters
        ("a" * 35, "a" * 30),
        (
            "this-is-a-very-long-branch-name-that-exceeds-thirty-characters",
            "this-is-a-very-long-branch-nam",
        ),
        ("exactly-30-characters-long-ok", "exactly-30-characters-long-ok"),
        (
            "31-characters-long-should-be-ab",
            "31-characters-long-should-be-a",
        ),  # Truncates to 30
        ("short", "short"),
        # Test truncation with trailing hyphen removal
        (
            "branch-name-with-dash-at-position-30-",
            "branch-name-with-dash-at-posit",
        ),
        # Test truncation that ends with hyphen is stripped
        (
            "12345678901234567890123456789-extra",
            "12345678901234567890123456789",
        ),  # Hyphen at position 30 stripped
    ],
)
def test_sanitize_branch_component(value: str, expected: str) -> None:
    assert sanitize_branch_component(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("feature X", "feature-x"),
        ("/ / ", "work"),
    ],
)
def test_default_branch_for_worktree(value: str, expected: str) -> None:
    assert default_branch_for_worktree(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Foo", "foo"),
        ("Add_Auth_Feature", "add-auth-feature"),
        ("My_Cool_Plan", "my-cool-plan"),
        ("FOO_BAR_BAZ", "foo-bar-baz"),
        ("feature__with___multiple___underscores", "feature-with-multiple-undersco"),
        ("name-with-hyphens", "name-with-hyphens"),
        ("Mixed_Case-Hyphen_Underscore", "mixed-case-hyphen-underscore"),
        ("@@weird!!name??", "weird-name"),
        ("   spaces   ", "spaces"),
        ("---", "work"),
        # Test truncation to 30 characters
        ("a" * 35, "a" * 30),
        (
            "this-is-a-very-long-worktree-name-that-exceeds-thirty-characters",
            "this-is-a-very-long-worktree-n",
        ),
        ("exactly-30-characters-long-ok", "exactly-30-characters-long-ok"),
        (
            "31-characters-long-should-be-ab",
            "31-characters-long-should-be-a",
        ),  # Truncates to 30
        # Test truncation with trailing hyphen removal
        (
            "worktree-name-with-dash-at-position-30-",
            "worktree-name-with-dash-at-pos",
        ),
        # Test truncation that ends with hyphen is stripped
        (
            "12345678901234567890123456789-extra",
            "12345678901234567890123456789",
        ),  # Hyphen at position 30 stripped
    ],
)
def test_sanitize_worktree_name(value: str, expected: str) -> None:
    assert sanitize_worktree_name(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("devclikit-extraction-plan", "devclikit-extraction"),
        ("my-feature-plan", "my-feature"),
        ("plan-for-auth", "for-auth"),
        ("plan-something", "something"),
        ("something-plan", "something"),
        ("something-plan-else", "something-else"),
        ("plan-my-plan-feature", "my-feature"),
        ("my-plan-feature-plan", "my-feature"),
        ("plan", "plan"),
        ("my_feature_plan", "my_feature"),
        ("my feature plan", "my feature"),
        ("my-feature_plan", "my-feature"),
        ("MY-FEATURE-PLAN", "MY-FEATURE"),
        ("My-Feature-Plan", "My-Feature"),
        ("my-feature-PLAN", "my-feature"),
        ("airplane-feature", "airplane-feature"),
        ("explain-system", "explain-system"),
        ("planted-tree", "planted-tree"),
        ("planning-session", "planning-session"),
        ("plans-document", "plans-document"),
        ("-plan-feature", "feature"),
        ("feature-plan-", "feature"),
        ("my-feature-implementation-plan", "my-feature"),
        ("implementation-plan-for-auth", "for-auth"),
        ("implementation_plan_feature", "feature"),
        ("feature implementation plan", "feature"),
        ("my-feature_implementation-plan", "my-feature"),
        ("implementation_plan-for-auth", "for-auth"),
        ("IMPLEMENTATION-PLAN-FEATURE", "FEATURE"),
        ("Implementation-Plan-Feature", "Feature"),
        ("my-IMPLEMENTATION-plan", "my"),
        ("my-implementation-plan-feature", "my-feature"),
        ("plan-implementation-plan", "implementation"),
        ("plan implementation plan", "implementation"),
        ("implementation-plan", "implementation"),
        ("implementation_plan", "implementation"),
        ("IMPLEMENTATION-PLAN", "IMPLEMENTATION"),
        ("reimplementation-feature", "reimplementation-feature"),
        ("implantation-system", "implantation-system"),
    ],
)
def test_strip_plan_from_filename(value: str, expected: str) -> None:
    assert strip_plan_from_filename(value) == expected


@pytest.mark.parametrize(
    ("name", "expected_base", "expected_number"),
    [
        ("my-feature", "my-feature", None),
        ("my-feature-2", "my-feature", 2),
        ("fix-42", "fix", 42),
        ("feature-3-test", "feature-3-test", None),  # Number in middle, not trailing
        ("test-123", "test", 123),
        ("no-number", "no-number", None),
        ("v2-feature-10", "v2-feature", 10),
    ],
)
def test_extract_trailing_number(
    name: str, expected_base: str, expected_number: int | None
) -> None:
    """Test extracting trailing numbers from worktree names."""
    base, number = extract_trailing_number(name)
    assert base == expected_base
    assert number == expected_number


def test_ensure_unique_worktree_name_first_time(tmp_path: Path) -> None:
    """Test first-time worktree creation gets only date prefix."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    result = ensure_unique_worktree_name("my-feature", workstacks_dir)

    # Should have date prefix in format YYYY-MM-DD-
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    assert result == f"{date_prefix}-my-feature"
    assert not (workstacks_dir / result).exists()


def test_ensure_unique_worktree_name_duplicate_same_day(tmp_path: Path) -> None:
    """Test duplicate worktree on same day adds -2 suffix."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    existing_name = f"{date_prefix}-my-feature"
    (workstacks_dir / existing_name).mkdir()

    result = ensure_unique_worktree_name("my-feature", workstacks_dir)

    assert result == f"{date_prefix}-my-feature-2"
    assert not (workstacks_dir / result).exists()
    assert (workstacks_dir / existing_name).exists()


def test_ensure_unique_worktree_name_multiple_duplicates(tmp_path: Path) -> None:
    """Test multiple duplicates increment correctly."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    (workstacks_dir / f"{date_prefix}-my-feature").mkdir()
    (workstacks_dir / f"{date_prefix}-my-feature-2").mkdir()
    (workstacks_dir / f"{date_prefix}-my-feature-3").mkdir()

    result = ensure_unique_worktree_name("my-feature", workstacks_dir)

    assert result == f"{date_prefix}-my-feature-4"


def test_ensure_unique_worktree_name_with_existing_number(tmp_path: Path) -> None:
    """Test name with existing number in base preserves it."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    result = ensure_unique_worktree_name("fix-v3", workstacks_dir)

    # Base name has number, should preserve it in date-prefixed name
    assert result == f"{date_prefix}-fix-v3"

    # Create it and try again
    (workstacks_dir / result).mkdir()
    result2 = ensure_unique_worktree_name("fix-v3", workstacks_dir)

    assert result2 == f"{date_prefix}-fix-v3-2"
