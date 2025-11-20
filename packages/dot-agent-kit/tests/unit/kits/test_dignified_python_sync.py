from pathlib import Path

import pytest


def test_shared_files_exist():
    """Verify all universal files exist in unified kit's shared directory."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"
    shared_dir = kits_dir / "dignified-python" / "shared"

    # Check shared universal reference files
    universal_files = [
        "exception-handling.md",
        "path-operations.md",
        "dependency-injection.md",
        "imports.md",
        "cli-patterns.md",
        "subprocess.md",
        "code-smells-dagster.md",
        "core-standards-universal.md",
        "patterns-reference-universal.md",
    ]

    for filename in universal_files:
        file_path = shared_dir / filename
        if not file_path.exists():
            pytest.fail(f"Shared file missing: dignified-python/shared/{filename}")


def test_type_annotations_files_exist():
    """Verify all version-specific type annotation files exist."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"
    type_annotations_dir = kits_dir / "dignified-python" / "shared" / "type-annotations"

    if not type_annotations_dir.exists():
        pytest.fail("Type annotations directory missing: dignified-python/shared/type-annotations/")

    # Check type annotation files for each version
    type_files = [
        "type-annotations-base.md",
        "type-annotations-310.md",
        "type-annotations-311.md",
        "type-annotations-312.md",
        "type-annotations-313.md",
    ]

    for filename in type_files:
        file_path = type_annotations_dir / filename
        if not file_path.exists():
            pytest.fail(
                f"Type annotation file missing: dignified-python/shared/type-annotations/{filename}"
            )


def test_unified_kit_structure():
    """Verify unified kit has required files and structure."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"
    unified_kit_dir = kits_dir / "dignified-python"

    # Check kit.yaml
    kit_yaml = unified_kit_dir / "kit.yaml"
    if not kit_yaml.exists():
        pytest.fail("Unified kit missing kit.yaml")

    # Check version-aware hook file
    hook_file = (
        unified_kit_dir / "kit_cli_commands" / "dignified-python" / "version_aware_reminder_hook.py"
    )
    if not hook_file.exists():
        pytest.fail("Unified kit missing hook file version_aware_reminder_hook.py")

    # Check each version-specific skill exists
    versions = ["310", "311", "312", "313"]
    for version in versions:
        skill_dir = unified_kit_dir / "skills" / f"dignified-python-{version}"

        # Check SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            pytest.fail(f"Unified kit missing SKILL.md for version {version}")

        # Check VERSION-CONTEXT.md
        version_context = skill_dir / "VERSION-CONTEXT.md"
        if not version_context.exists():
            pytest.fail(f"Unified kit missing VERSION-CONTEXT.md for version {version}")


def test_skill_references_correct_types():
    """Verify each SKILL.md references correct type-annotations file."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"

    versions = ["310", "311", "312", "313"]

    for version in versions:
        skill_md = (
            kits_dir / "dignified-python" / "skills" / f"dignified-python-{version}" / "SKILL.md"
        )
        if not skill_md.exists():
            continue  # Skip if file doesn't exist (caught by other test)

        content = skill_md.read_text(encoding="utf-8")
        expected_type_annotations = f"type-annotations-{version}.md"
        expected_pattern_table = f"pattern-table-{version}.md"

        # Check if SKILL.md references type-annotations directly or via pattern-table
        has_direct_reference = expected_type_annotations in content
        has_pattern_table_reference = expected_pattern_table in content

        if not (has_direct_reference or has_pattern_table_reference):
            pytest.fail(
                f"Skill {version} SKILL.md does not reference {expected_type_annotations}\n"
                f"Expected to find either direct reference to type-annotations-{version}.md "
                f"or include of pattern-table-{version}.md"
            )


def test_no_version_specific_language_in_shared():
    """Verify shared files don't contain 'Python 3.13+' or similar."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"
    shared_dir = kits_dir / "dignified-python" / "shared"

    # Patterns that should NOT appear in shared files
    prohibited_patterns = [
        "Python 3.13+",
        "3.13 and above",
        "3.13 or higher",
        "Python 3.13 only",
    ]

    # Get all markdown files in shared directory (excluding type-annotations subdirectory)
    shared_files = [f for f in shared_dir.glob("*.md")]

    for file_path in shared_files:
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            if pattern in content:
                pytest.fail(
                    f"Shared file {file_path.name} contains version-specific "
                    f"language: '{pattern}'\n"
                    f"Shared files must be version-neutral."
                )
