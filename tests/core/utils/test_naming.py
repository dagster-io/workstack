import pytest

from workstack.cli.commands.create import (
    default_branch_for_worktree,
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
        ("feature__with___multiple___underscores", "feature-with-multiple-underscores"),
        ("name-with-hyphens", "name-with-hyphens"),
        ("Mixed_Case-Hyphen_Underscore", "mixed-case-hyphen-underscore"),
        ("@@weird!!name??", "weird-name"),
        ("   spaces   ", "spaces"),
        ("---", "work"),
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
