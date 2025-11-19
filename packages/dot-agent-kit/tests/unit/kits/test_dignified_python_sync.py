from pathlib import Path

import pytest


def test_universal_standards_are_synchronized():
    """Ensure all Dignified Python kits have identical universal standards."""
    package_root = Path(__file__).parent.parent.parent.parent
    kits_dir = package_root / "src" / "dot_agent_kit" / "data" / "kits"

    source = kits_dir / "dignified-python-shared" / "universal-python-standards.md"
    py310_copy = kits_dir / "dignified-python-310" / "skills" / "dignified-python" / "UNIVERSAL.md"
    py313_copy = kits_dir / "dignified-python-313" / "skills" / "dignified-python" / "UNIVERSAL.md"

    if not source.exists():
        pytest.fail("Source file missing: dignified-python-shared/universal-python-standards.md")

    source_content = source.read_text(encoding="utf-8")

    if py310_copy.exists():
        py310_content = py310_copy.read_text(encoding="utf-8")
        if source_content != py310_content:
            pytest.fail(
                "Python 3.10 universal standards out of sync.\n"
                "Run: make sync-dignified-python-universal"
            )

    if py313_copy.exists():
        py313_content = py313_copy.read_text(encoding="utf-8")
        if source_content != py313_content:
            pytest.fail(
                "Python 3.13 universal standards out of sync.\n"
                "Run: make sync-dignified-python-universal"
            )
