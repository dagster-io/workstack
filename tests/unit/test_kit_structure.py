"""Structural tests for kit CLI command organization.

This test enforces that kit CLI commands in src/erk/data/kits/ are symlinks
pointing to the canonical source in packages/dot-agent-kit/.

Following the pattern established in the gt kit, all kit CLI commands should:
1. Have their source of truth in packages/dot-agent-kit/
2. Be symlinked from src/erk/data/kits/

This prevents duplication and ensures a single source of truth.
"""

from pathlib import Path


def test_erk_kit_cli_commands_are_symlinks() -> None:
    """Test that erk kit CLI commands are symlinks to dot-agent-kit."""
    repo_root = Path(__file__).parent.parent.parent
    src_kit_dir = repo_root / "src" / "erk" / "data" / "kits" / "erk" / "kit_cli_commands" / "erk"
    pkg_kit_dir = (
        repo_root
        / "packages"
        / "dot-agent-kit"
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / "erk"
        / "kit_cli_commands"
        / "erk"
    )

    # Get all Python files in src (excluding __init__.py and __pycache__)
    src_files = [
        f
        for f in src_kit_dir.glob("*.py")
        if f.name != "__init__.py" and "__pycache__" not in str(f)
    ]

    # Files that should NOT be symlinks (exist only in src/)
    src_only_files = {
        "post_completion_comment.py",
        "post_progress_comment.py",
    }

    for src_file in src_files:
        if src_file.name in src_only_files:
            # These files should be regular files, not symlinks
            assert not src_file.is_symlink(), (
                f"{src_file.name} should be a regular file (not in packages/dot-agent-kit), "
                f"but it's a symlink"
            )
            continue

        # All other files should be symlinks
        symlink_path = (
            "../../../../../../../packages/dot-agent-kit/src/"
            f"dot_agent_kit/data/kits/erk/kit_cli_commands/erk/{src_file.name}"
        )
        assert src_file.is_symlink(), (
            f"{src_file.name} should be a symlink to packages/dot-agent-kit, "
            f"but it's a regular file. "
            f"Convert it to a symlink: "
            f"cd {src_kit_dir} && rm {src_file.name} && "
            f"ln -s {symlink_path} {src_file.name}"
        )

        # Verify the symlink target exists
        target = src_file.resolve()
        assert target.exists(), (
            f"{src_file.name} is a symlink but its target doesn't exist: {target}"
        )

        # Verify the symlink points to the correct location (in packages/dot-agent-kit/)
        expected_target = pkg_kit_dir / src_file.name
        assert target == expected_target, (
            f"{src_file.name} symlink points to wrong location.\n"
            f"Expected: {expected_target}\n"
            f"Actual: {target}"
        )


def test_gt_kit_cli_commands_are_symlinks() -> None:
    """Test that gt kit CLI commands are symlinks to dot-agent-kit."""
    repo_root = Path(__file__).parent.parent.parent
    src_kit_dir = repo_root / "src" / "erk" / "data" / "kits" / "gt" / "kit_cli_commands" / "gt"
    pkg_kit_dir = (
        repo_root
        / "packages"
        / "dot-agent-kit"
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / "gt"
        / "kit_cli_commands"
        / "gt"
    )

    # Files that should be symlinks (moved to dot-agent-kit)
    symlinked_files = {
        "simple_submit.py",
    }

    for filename in symlinked_files:
        src_file = src_kit_dir / filename

        # Should exist and be a symlink
        assert src_file.exists(), (
            f"{filename} should exist in src/erk/data/kits/gt/kit_cli_commands/gt/"
        )
        assert src_file.is_symlink(), (
            f"{filename} should be a symlink to packages/dot-agent-kit, but it's a regular file"
        )

        # Verify the symlink target exists
        target = src_file.resolve()
        assert target.exists(), f"{filename} is a symlink but its target doesn't exist: {target}"

        # Verify the symlink points to the correct location
        expected_target = pkg_kit_dir / filename
        assert target == expected_target, (
            f"{filename} symlink points to wrong location.\n"
            f"Expected: {expected_target}\n"
            f"Actual: {target}"
        )


def test_symlinked_files_point_to_correct_location() -> None:
    """Test that kit CLI command symlinks point to the correct location.

    This verifies that any files that ARE symlinks in src/erk/data/kits/
    correctly point to their source in packages/dot-agent-kit/.
    """
    repo_root = Path(__file__).parent.parent.parent

    kits = ["erk", "gt"]

    for kit_name in kits:
        src_kit_dir = (
            repo_root / "src" / "erk" / "data" / "kits" / kit_name / "kit_cli_commands" / kit_name
        )
        pkg_kit_dir = (
            repo_root
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_name
            / "kit_cli_commands"
            / kit_name
        )

        if not src_kit_dir.exists():
            continue

        # Check all Python files in src
        for src_file in src_kit_dir.glob("*.py"):
            if src_file.name == "__init__.py":
                continue

            # If it's a symlink, verify it points to the correct location
            if src_file.is_symlink():
                target = src_file.resolve()
                expected_target = pkg_kit_dir / src_file.name

                # Verify target exists
                assert target.exists(), (
                    f"{kit_name} kit: {src_file.name} is a symlink "
                    f"but target doesn't exist: {target}"
                )

                # Verify target is in packages/dot-agent-kit/
                assert target == expected_target, (
                    f"{kit_name} kit: {src_file.name} symlink points to wrong location.\n"
                    f"Expected: {expected_target}\n"
                    f"Actual: {target}"
                )
