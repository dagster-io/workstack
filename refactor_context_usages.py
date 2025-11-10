#!/usr/bin/env python3
"""Automated refactoring script to replace FakeGlobalConfigOps with GlobalConfig.

This script:
1. Finds all occurrences of FakeGlobalConfigOps construction
2. Replaces with GlobalConfig(...) with all required fields
3. Updates WorkstackContext(...) to use .for_test(...) factory
"""

import re
from pathlib import Path


def refactor_file(file_path: Path) -> tuple[bool, str]:
    """Refactor a single file to use GlobalConfig and WorkstackContext.for_test().

    Returns:
        Tuple of (changed, error_message)
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Pattern 1a: FakeGlobalConfigOps() with no arguments
    content = re.sub(
        r"FakeGlobalConfigOps\(\)",
        (
            "GlobalConfig(\n"
            '            workstacks_root=Path("/fake/workstacks"),\n'
            "            use_graphite=False,\n"
            "            shell_setup_complete=False,\n"
            "            show_pr_info=True,\n"
            "            show_pr_checks=False,\n"
            "        )"
        ),
        content,
    )

    # Pattern 1b: FakeGlobalConfigOps(use_graphite=True/False) only
    def replace_graphite_only(match: re.Match[str]) -> str:
        graphite = match.group(1)
        return (
            f"GlobalConfig(\n"
            f'            workstacks_root=Path("/fake/workstacks"),\n'
            f"            use_graphite={graphite},\n"
            f"            shell_setup_complete=False,\n"
            f"            show_pr_info=True,\n"
            f"            show_pr_checks=False,\n"
            f"        )"
        )

    content = re.sub(
        r"FakeGlobalConfigOps\(use_graphite=(True|False)\)", replace_graphite_only, content
    )

    # Pattern 1c: FakeGlobalConfigOps(show_pr_info=True/False) only
    def replace_show_pr_info_only(match: re.Match[str]) -> str:
        show_pr_info = match.group(1)
        return (
            f"GlobalConfig(\n"
            f'            workstacks_root=Path("/fake/workstacks"),\n'
            f"            use_graphite=False,\n"
            f"            shell_setup_complete=False,\n"
            f"            show_pr_info={show_pr_info},\n"
            f"            show_pr_checks=False,\n"
            f"        )"
        )

    content = re.sub(
        r"FakeGlobalConfigOps\(show_pr_info=(True|False)\)", replace_show_pr_info_only, content
    )

    # Pattern 1d: FakeGlobalConfigOps(workstacks_root=...) only
    def replace_root_only(match: re.Match[str]) -> str:
        root = match.group(1)
        return (
            f"GlobalConfig(\n"
            f"            workstacks_root={root},\n"
            f"            use_graphite=False,\n"
            f"            shell_setup_complete=False,\n"
            f"            show_pr_info=True,\n"
            f"            show_pr_checks=False,\n"
            f"        )"
        )

    content = re.sub(r"FakeGlobalConfigOps\(workstacks_root=([^)]+)\)", replace_root_only, content)

    # Pattern 1e: FakeGlobalConfigOps with exists + workstacks_root +
    # use_graphite (original pattern)
    fake_config_pattern = re.compile(
        r"FakeGlobalConfigOps\s*\(\s*"
        r"(?:exists\s*=\s*(?P<exists>True|False)\s*,\s*)?"
        r"workstacks_root\s*=\s*(?P<root>[^,]+)\s*,\s*"
        r"use_graphite\s*=\s*(?P<graphite>True|False)\s*,?\s*"
        r"\)",
        re.MULTILINE,
    )

    def replace_fake_config(match: re.Match[str]) -> str:
        """Replace FakeGlobalConfigOps with GlobalConfig."""
        root = match.group("root")
        graphite = match.group("graphite")

        return (
            f"GlobalConfig(\n"
            f"            workstacks_root={root},\n"
            f"            use_graphite={graphite},\n"
            f"            shell_setup_complete=False,\n"
            f"            show_pr_info=True,\n"
            f"            show_pr_checks=False,\n"
            f"        )"
        )

    content = fake_config_pattern.sub(replace_fake_config, content)

    # Pattern 2: Replace WorkstackContext(...) with WorkstackContext.for_test(...)
    # Find WorkstackContext constructor calls and replace with .for_test()
    context_pattern = re.compile(
        r"(?P<indent>[ \t]*)test_ctx\s*=\s*WorkstackContext\s*\(\s*\n"
        r"(?P<indent2>[ \t]*)git_ops\s*=\s*(?P<git_ops>[^,]+)\s*,\s*\n"
        r"(?P<indent3>[ \t]*)global_config_ops\s*=\s*(?P<config>[^,]+)\s*,\s*\n"
        r"(?P<indent4>[ \t]*)github_ops\s*=\s*[^,]+\s*,\s*\n"
        r"(?P<indent5>[ \t]*)graphite_ops\s*=\s*[^,]+\s*,\s*\n"
        r"(?P<indent6>[ \t]*)shell_ops\s*=\s*[^,]+\s*,\s*\n"
        r"(?P<indent7>[ \t]*)cwd\s*=\s*(?P<cwd>[^,]+)\s*,\s*\n"
        r"(?P<indent8>[ \t]*)dry_run\s*=\s*(?P<dry_run>True|False)\s*,?\s*\n"
        r"(?P<indent9>[ \t]*)\)",
        re.MULTILINE,
    )

    def replace_context(match: re.Match[str]) -> str:
        """Replace WorkstackContext with .for_test() factory."""
        indent = match.group("indent")
        git_ops = match.group("git_ops")
        config = match.group("config")
        cwd = match.group("cwd")
        dry_run = match.group("dry_run")

        # Replace global_config_ops with global_config
        result = (
            f"{indent}test_ctx = WorkstackContext.for_test(\n"
            f"{indent}    git_ops={git_ops},\n"
            f"{indent}    global_config={config},\n"
            f"{indent}    cwd={cwd},\n"
        )

        # Only add dry_run if it's True (default is False)
        if dry_run == "True":
            result += f"{indent}    dry_run={dry_run},\n"

        result += f"{indent})"

        return result

    content = context_pattern.sub(replace_context, content)

    # Save if changed
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return (True, "")

    return (False, "No changes needed")


def main() -> None:
    """Run refactoring on all test files."""
    # Files to refactor (from .PHASE_3A_PROGRESS.md)
    files_to_refactor = [
        # Workspace commands
        "tests/commands/workspace/test_create.py",
        "tests/commands/workspace/test_rm.py",
        "tests/commands/workspace/test_rename.py",
        "tests/commands/workspace/test_move.py",
        "tests/commands/workspace/test_consolidate.py",
        # Navigation commands
        "tests/commands/navigation/test_up.py",
        "tests/commands/navigation/test_switch_up_down.py",
        "tests/commands/navigation/test_jump.py",
        "tests/commands/navigation/test_graphite_find_worktrees.py",
        "tests/commands/navigation/test_down.py",
        # Display commands
        "tests/commands/display/test_tree.py",
        "tests/commands/display/list/test_trunk_detection.py",
        "tests/commands/display/list/test_stacks.py",
        "tests/commands/display/list/test_root_filtering.py",
        "tests/commands/display/list/test_pr_info.py",
        "tests/commands/display/list/test_basic.py",
        # Other command tests
        "tests/commands/graphite/test_land_stack.py",
        "tests/commands/graphite/test_gt_branches.py",
        "tests/commands/sync/test_sync.py",
        "tests/commands/test_status_with_fakes.py",
        "tests/commands/setup/test_init.py",
        "tests/commands/setup/test_config.py",
        "tests/commands/shell/test_prepare_cwd_recovery.py",
        # Unit/integration tests
        "tests/unit/status/test_graphite_stack_collector.py",
        "tests/unit/status/test_github_pr_collector.py",
        "tests/unit/detection/test_trunk_detection.py",
        "tests/integration/test_real_global_config.py",
        "tests/integration/test_land_stack_worktree.py",
        "tests/integration/test_dryrun_integration.py",
    ]

    base_dir = Path(__file__).parent
    changed_files = []
    unchanged_files = []
    error_files = []

    for file_path_str in files_to_refactor:
        file_path = base_dir / file_path_str
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path_str}")
            error_files.append((file_path_str, "File not found"))
            continue

        changed, error = refactor_file(file_path)
        if changed:
            print(f"✓ Refactored: {file_path_str}")
            changed_files.append(file_path_str)
        elif error:
            print(f"⚠️  {file_path_str}: {error}")
            unchanged_files.append(file_path_str)
        else:
            print(f"✓ Already refactored: {file_path_str}")
            unchanged_files.append(file_path_str)

    print("\n" + "=" * 60)
    print(f"✅ Changed: {len(changed_files)} files")
    print(f"ℹ️  Unchanged: {len(unchanged_files)} files")
    print(f"❌ Errors: {len(error_files)} files")

    if error_files:
        print("\nError files:")
        for file_name, error in error_files:
            print(f"  - {file_name}: {error}")


if __name__ == "__main__":
    main()
