import os
import subprocess
from pathlib import Path
from typing import NamedTuple

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext, regenerate_context
from workstack.core.graphite_ops import BranchMetadata

"""
Workstack land-stack command: Land stacked PRs sequentially from bottom to top.

## Module Overview

Purpose: Merges a stack of Graphite pull requests sequentially from bottom
(closest to trunk) to top (current branch), with restacking between each merge.

Stack direction: main (bottom) → feat-1 → feat-2 → feat-3 (top)
Landing order: feat-1, then feat-2, then feat-3 (bottom to top)

Integration: Works with Graphite (gt CLI), GitHub CLI (gh), and worktrees.

## Complete 5-Phase Workflow

### Phase 1: Discovery & Validation
- Build list of branches from bottom of stack to current branch
- Check Graphite enabled, clean working directory, not on trunk, no worktree conflicts
- Verify all branches have open PRs
- Check GitHub for merge conflicts (prevents landing failures)

### Phase 2: User Confirmation
- Display PRs to land and get user confirmation (or --force to skip)

### Phase 3: Landing Sequence
For each branch from bottom to top:
  1. Checkout branch (or verify already on branch)
  2. Verify stack integrity (parent is trunk after previous restacks)
  3. Update PR base branch on GitHub if stale
  4. Merge PR via `gh pr merge --squash --auto`
  5. Restack remaining branches via `gt sync -f`
  6. Submit updated PRs to GitHub

### Phase 4: Cleanup
- Remove merged branch worktrees
- Navigate to safe branch (trunk or next unmerged branch)
- Regenerate context after directory changes

### Phase 5: Final State
- Display what was accomplished
- Show current branch and merged branches

## Key Concepts

**Stack Direction:**
- Bottom (downstack) = trunk (main/master)
- Top (upstack) = leaves (feature branches furthest from trunk)
- Commands like `gt up` / `gt down` navigate this direction

**Restacking:**
After each PR merge, `gt sync -f` rebases all remaining branches onto the
new trunk state. This maintains stack integrity as PRs are landed.

**Worktree Conflicts:**
Git prevents checking out a branch in multiple worktrees. Phase 1 validation
detects this and suggests `workstack consolidate` to fix.

**Context Regeneration:**
After `os.chdir()` calls, must regenerate WorkstackContext to update `ctx.cwd`.
This happens in Phase 4 after navigation operations.

## Error Handling Strategy

**Fail Fast:**
All validation happens in Phase 1, before user confirmation. If any
precondition fails, command exits immediately with helpful error message.

**Error Types:**
- `SystemExit(1)` - All validation failures and expected errors
- `subprocess.CalledProcessError` - git/gh/gt command failures (caught and converted to SystemExit)
- `FileNotFoundError` - Missing CLI tools (caught and converted to SystemExit)

**Error Messages:**
All errors include:
- Clear description of what failed
- Context (branch names, paths, PR numbers)
- Concrete fix steps ("To fix: ...")
"""


def _emit(message: str, *, script_mode: bool, error: bool = False) -> None:
    """Emit a message to stdout or stderr based on script mode.

    In script mode, ALL output goes to stderr (so the shell wrapper can capture
    only the activation script from stdout). The `error` parameter has no effect
    in script mode since everything is already sent to stderr.

    In non-script mode, output goes to stdout by default, unless `error=True`.

    Args:
        message: Text to output.
        script_mode: True when running in --script mode (all output to stderr).
        error: Force stderr output in non-script mode (ignored in script mode).
    """
    click.echo(message, err=error or script_mode)


class BranchPR(NamedTuple):
    """Branch with associated PR information."""

    branch: str
    pr_number: int
    title: str


def _format_cli_command(cmd: str, check: str) -> str:
    """Format a CLI command operation for display.

    Args:
        cmd: The CLI command string (e.g., "git checkout main")
        check: Checkmark string to append

    Returns:
        Formatted operation string with styling
    """
    cmd_styled = click.style(cmd, fg="white", dim=True)
    return f"  {cmd_styled} {check}"


def _format_description(description: str, check: str) -> str:
    """Format an internal operation description for display.

    Args:
        description: Description text (will be wrapped in brackets)
        check: Checkmark string to append

    Returns:
        Formatted description string with dim styling
    """
    desc_styled = click.style(f"[{description}]", dim=True)
    return f"  {desc_styled} {check}"


def _get_branches_to_land(ctx: WorkstackContext, repo_root: Path, current_branch: str) -> list[str]:
    """Get branches to land from bottom of stack up to and including current branch.

    For PR landing, we need to land from the bottom (closest to trunk) upward,
    as each PR depends on the one below it. This returns all branches from the
    start of the stack up to the current branch.

    Args:
        ctx: WorkstackContext with access to graphite operations
        repo_root: Repository root directory
        current_branch: Name of the current branch

    Returns:
        List of branch names from bottom of stack to current (inclusive, excluding trunk)
        Empty list if branch not in stack
    """
    # Get full stack (trunk to leaves)
    stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
    if stack is None:
        return []

    # Get all branch metadata to filter out trunk branches
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        return []

    # Filter stack to exclude trunk branches
    filtered_stack = [b for b in stack if b in all_branches and not all_branches[b].is_trunk]

    # Find current branch index
    if current_branch not in filtered_stack:
        return []

    current_idx = filtered_stack.index(current_branch)

    # Return slice from start to current (inclusive) - bottom to current for PR landing
    return filtered_stack[: current_idx + 1]


def _validate_landing_preconditions(
    ctx: WorkstackContext,
    repo_root: Path,
    current_branch: str | None,
    branches_to_land: list[str],
    *,
    script_mode: bool,
) -> None:
    """Validate all preconditions for landing are met.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        current_branch: Current branch name (None if detached HEAD)
        branches_to_land: List of branches to land
        script_mode: True when running in --script mode (output to stderr)

    Raises:
        SystemExit: If any precondition fails
    """
    # Check Graphite enabled
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        _emit(
            "Error: 'workstack land-stack' requires Graphite.\n\n"
            "To fix:\n"
            "  • Run: workstack config set use-graphite true\n"
            "  • Install Graphite CLI if needed: brew install withgraphite/tap/graphite",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check not detached HEAD
    if current_branch is None:
        _emit(
            "Error: HEAD is detached (not on a branch)\n\n"
            "To fix:\n"
            "  • Check out a branch: git checkout <branch-name>",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check no uncommitted changes in current worktree
    if ctx.git_ops.has_uncommitted_changes(ctx.cwd):
        _emit(
            f"Error: Current worktree has uncommitted changes\n"
            f"Path: {ctx.cwd}\n"
            f"Branch: {current_branch}\n\n"
            "Landing requires a clean working directory.\n\n"
            "To fix:\n"
            "  • Commit your changes: git add . && git commit -m 'message'\n"
            "  • Stash your changes: git stash\n"
            "  • Discard your changes: git reset --hard HEAD",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check current branch not trunk
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if current_branch in all_branches and all_branches[current_branch].is_trunk:
        _emit(
            f"Error: Cannot land trunk branch '{current_branch}'\n"
            "Trunk branches (main/master) cannot be landed.\n\n"
            "To fix:\n"
            "  • Check out a feature branch: git checkout <feature-branch>",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Validate stack exists
    if not branches_to_land:
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
        if stack is None:
            _emit(
                f"Error: Branch '{current_branch}' is not tracked by Graphite\n\n"
                "To fix:\n"
                "  • Track the branch with Graphite: gt create -s\n"
                "  • Or switch to a Graphite-tracked branch",
                script_mode=script_mode,
                error=True,
            )
        else:
            _emit(
                f"Error: No branches to land\n"
                f"Branch '{current_branch}' may already be landed or is a trunk branch.",
                script_mode=script_mode,
                error=True,
            )
        raise SystemExit(1)

    # Check no branches in stack are checked out in other worktrees
    current_worktree = ctx.cwd.resolve()
    worktree_conflicts: list[tuple[str, Path]] = []

    for branch in branches_to_land:
        worktree_path = ctx.git_ops.is_branch_checked_out(repo_root, branch)
        if worktree_path and worktree_path.resolve() != current_worktree:
            worktree_conflicts.append((branch, worktree_path))

    if worktree_conflicts:
        _emit(
            "Error: Cannot land stack - branches are checked out in multiple worktrees\n\n"
            "The following branches are checked out in other worktrees:",
            script_mode=script_mode,
            error=True,
        )
        for branch, path in worktree_conflicts:
            branch_styled = click.style(branch, fg="yellow")
            path_styled = click.style(str(path), fg="white", dim=True)
            _emit(f"  • {branch_styled} → {path_styled}", script_mode=script_mode, error=True)

        _emit(
            "\nGit does not allow checking out a branch that is already checked out\n"
            "in another worktree. To land this stack, you need to consolidate all\n"
            "branches into the current worktree first.\n\n"
            "To fix:\n"
            "  • Run: workstack consolidate\n"
            "  • This will remove other worktrees for branches in this stack\n"
            "  • Then retry: workstack land-stack",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)


def _validate_branches_have_prs(
    ctx: WorkstackContext, repo_root: Path, branches: list[str], *, script_mode: bool
) -> list[BranchPR]:
    """Validate all branches have open PRs.

    Args:
        ctx: WorkstackContext with access to GitHub operations
        repo_root: Repository root directory
        branches: List of branch names to validate
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of BranchPR for all valid branches

    Raises:
        SystemExit: If any branch has invalid PR state
    """
    errors: list[str] = []
    valid_branches: list[BranchPR] = []

    for branch in branches:
        pr_info = ctx.github_ops.get_pr_status(repo_root, branch, debug=False)

        if pr_info.state == "NONE":
            errors.append(f"No PR found for branch '{branch}'")
        elif pr_info.state == "MERGED":
            errors.append(f"PR #{pr_info.pr_number} for '{branch}' is already merged")
        elif pr_info.state == "CLOSED":
            errors.append(f"PR #{pr_info.pr_number} for '{branch}' is closed")
        elif (
            pr_info.state == "OPEN" and pr_info.pr_number is not None and pr_info.title is not None
        ):
            valid_branches.append(BranchPR(branch, pr_info.pr_number, pr_info.title))
        else:
            errors.append(f"Unexpected PR state for '{branch}': {pr_info.state}")

    if errors:
        _emit(
            "Error: Cannot land stack\n\nThe following branches have issues:",
            script_mode=script_mode,
            error=True,
        )
        for error in errors:
            _emit(f"  • {error}", script_mode=script_mode, error=True)
        raise SystemExit(1)

    return valid_branches


def _validate_pr_mergeability(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[BranchPR],
    *,
    script_mode: bool,
) -> None:
    """Validate all PRs are mergeable (no conflicts)."""
    conflicts: list[tuple[str, int]] = []

    for branch_pr in branches:
        mergeability = ctx.github_ops.get_pr_mergeability(repo_root, branch_pr.pr_number)

        if mergeability is None:
            # API error - log warning but don't fail
            continue

        if mergeability.mergeable == "CONFLICTING":
            conflicts.append((branch_pr.branch, branch_pr.pr_number))
        elif mergeability.mergeable == "UNKNOWN":
            # GitHub hasn't computed yet - log warning but don't fail
            _emit(
                f"⚠️  Warning: PR #{branch_pr.pr_number} mergeability unknown",
                script_mode=script_mode,
                error=False,
            )

    if conflicts:
        # Show error with all conflicts and resolution steps
        _emit(
            "Error: Cannot land stack - PRs have merge conflicts\n",
            script_mode=script_mode,
            error=True,
        )
        for branch, pr_num in conflicts:
            _emit(
                f"  • PR #{pr_num} ({branch}): has conflicts with main",
                script_mode=script_mode,
                error=True,
            )
        _emit("\nTo fix:", script_mode=script_mode, error=True)
        _emit("  1. Fetch latest: git fetch origin main", script_mode=script_mode, error=True)
        _emit("  2. Rebase stack: gt stack rebase", script_mode=script_mode, error=True)
        raise SystemExit(1)


def _show_landing_plan(
    current_branch: str,
    trunk_branch: str,
    branches: list[BranchPR],
    *,
    force: bool,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Display landing plan and get user confirmation.

    Args:
        current_branch: Name of current branch
        trunk_branch: Name of trunk branch (displayed at bottom)
        branches: List of BranchPR to land (bottom to top order)
        force: If True, skip confirmation
        dry_run: If True, skip confirmation and add dry-run prefix
        script_mode: True when running in --script mode (output to stderr)

    Raises:
        SystemExit: If user declines confirmation
    """
    # Display header
    header = "📋 Summary"
    if dry_run:
        header += click.style(" (dry run)", fg="bright_black")
    _emit(click.style(f"\n{header}", bold=True), script_mode=script_mode)
    _emit("", script_mode=script_mode)

    # Display summary
    pr_text = "PR" if len(branches) == 1 else "PRs"
    _emit(f"Landing {len(branches)} {pr_text}:", script_mode=script_mode)

    # Display PRs in format: #PR (branch → target) - title
    # Show in landing order (bottom to top)
    for branch_pr in branches:
        pr_styled = click.style(f"#{branch_pr.pr_number}", fg="cyan")
        branch_styled = click.style(branch_pr.branch, fg="yellow")
        trunk_styled = click.style(trunk_branch, fg="yellow")
        title_styled = click.style(branch_pr.title, fg="bright_magenta")

        line = f"  {pr_styled} ({branch_styled} → {trunk_styled}) - {title_styled}"
        _emit(line, script_mode=script_mode)

    _emit("", script_mode=script_mode)

    # Confirmation or force flag
    if dry_run:
        # No additional message needed - already indicated in header
        pass
    elif force:
        _emit("[--force flag set, proceeding without confirmation]", script_mode=script_mode)
    else:
        if not click.confirm("Proceed with landing these PRs?", default=False, err=script_mode):
            _emit("Landing cancelled.", script_mode=script_mode)
            raise SystemExit(0)


def _get_all_children(branch: str, all_branches: dict[str, BranchMetadata]) -> list[str]:
    """Get all children (upstack branches) of a branch recursively.

    Args:
        branch: Branch name to get children for
        all_branches: Dict of all branch metadata from get_all_branches()

    Returns:
        List of all children branch names (direct and indirect), in order from
        closest to furthest upstack. Returns empty list if branch has no children.
    """
    result: list[str] = []

    branch_metadata = all_branches.get(branch)
    if not branch_metadata or not branch_metadata.children:
        return result

    # Process direct children
    for child in branch_metadata.children:
        result.append(child)
        # Recursively get children of children
        result.extend(_get_all_children(child, all_branches))

    return result


def _land_branch_sequence(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[BranchPR],
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> list[str]:
    """Land branches sequentially, one at a time with restack between each.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branches: List of BranchPR to land
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of successfully merged branch names

    Raises:
        subprocess.CalledProcessError: If git/gh/gt commands fail
        Exception: If other operations fail
    """
    merged_branches: list[str] = []

    check = click.style("✓", fg="green")

    for _idx, branch_pr in enumerate(branches, 1):
        branch = branch_pr.branch
        pr_number = branch_pr.pr_number

        # Get parent for display
        parent = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo_root, branch)
        parent_display = parent if parent else "trunk"

        # Print section header
        _emit("", script_mode=script_mode)
        pr_styled = click.style(f"#{pr_number}", fg="cyan")
        branch_styled = click.style(branch, fg="yellow")
        parent_styled = click.style(parent_display, fg="yellow")
        msg = f"Landing PR {pr_styled} ({branch_styled} → {parent_styled})..."
        _emit(msg, script_mode=script_mode)

        # Phase 1: Checkout
        if dry_run:
            _emit(_format_cli_command(f"git checkout {branch}", check), script_mode=script_mode)
        else:
            # Check if we're already on the target branch (LBYL)
            # This handles the case where we're in a linked worktree on the branch being landed
            current_branch = ctx.git_ops.get_current_branch(Path.cwd())
            if current_branch != branch:
                # Only checkout if we're not already on the branch
                ctx.git_ops.checkout_branch(repo_root, branch)
                _emit(_format_cli_command(f"git checkout {branch}", check), script_mode=script_mode)
            else:
                # Already on branch, display as already done
                already_msg = f"already on {branch}"
                _emit(_format_description(already_msg, check), script_mode=script_mode)

        # Phase 2: Verify stack integrity
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)

        # Parent should be trunk after previous restacks
        if parent is None or parent not in all_branches or not all_branches[parent].is_trunk:
            if not dry_run:
                raise RuntimeError(
                    f"Stack integrity broken: {branch} parent is '{parent}', "
                    f"expected trunk branch. Previous restack may have failed."
                )

        # Show specific verification message with branch and expected parent
        trunk_name = parent if parent else "trunk"
        desc = _format_description(f"verify {branch} parent is {trunk_name}", check)
        _emit(desc, script_mode=script_mode)

        # Phase 3: Merge PR
        if dry_run:
            merge_cmd = f"gh pr merge {pr_number} --squash"
            _emit(_format_cli_command(merge_cmd, check), script_mode=script_mode)
            merged_branches.append(branch)
        else:
            # Use gh pr merge with squash strategy (Graphite's default)
            cmd = ["gh", "pr", "merge", str(pr_number), "--squash"]
            result = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            if verbose:
                _emit(result.stdout, script_mode=script_mode)

            merge_cmd = f"gh pr merge {pr_number} --squash"
            _emit(_format_cli_command(merge_cmd, check), script_mode=script_mode)
            merged_branches.append(branch)

        # Phase 4: Restack
        if dry_run:
            _emit(_format_cli_command("gt sync -f", check), script_mode=script_mode)
        else:
            ctx.graphite_ops.sync(repo_root, force=True, quiet=not verbose)
            _emit(_format_cli_command("gt sync -f", check), script_mode=script_mode)

        # Phase 5: Force-push rebased branches
        # After gt sync -f rebases remaining branches locally,
        # push them to GitHub so subsequent PR merges will succeed
        #
        # Get ALL upstack branches from the full Graphite tree, not just
        # the branches in our landing list. After landing feat-1 in a stack
        # like main → feat-1 → feat-2 → feat-3, we need to force-push BOTH
        # feat-2 and feat-3, even if we're only landing up to feat-2.
        all_branches_metadata = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
        upstack_branches: list[str] = []
        if all_branches_metadata:
            # Get all children of the current branch recursively
            upstack_branches = _get_all_children(branch, all_branches_metadata)
            if upstack_branches:
                for upstack_branch in upstack_branches:
                    if dry_run:
                        submit_cmd = f"gt submit --branch {upstack_branch} --no-edit"
                        _emit(_format_cli_command(submit_cmd, check), script_mode=script_mode)
                    else:
                        ctx.graphite_ops.submit_branch(repo_root, upstack_branch, quiet=not verbose)
                        submit_cmd = f"gt submit --branch {upstack_branch} --no-edit"
                        _emit(_format_cli_command(submit_cmd, check), script_mode=script_mode)

        # Phase 6: Update PR base branches on GitHub after force-push
        # After force-pushing rebased commits, update stale PR bases on GitHub
        # This must happen AFTER force-push because GitHub rejects base changes
        # when the new base doesn't contain the PR's head commits
        #
        # For each upstack branch that was force-pushed:
        # 1. Get its updated parent from Graphite metadata
        # 2. Get its PR number and current base from GitHub
        # 3. Update base if stale (current base != expected parent)
        if all_branches_metadata and upstack_branches:
            for upstack_branch in upstack_branches:
                # Get updated parent from Graphite metadata (should be correct after sync)
                branch_metadata = all_branches_metadata.get(upstack_branch)
                if branch_metadata is None:
                    continue

                expected_parent = branch_metadata.parent
                if expected_parent is None:
                    continue

                # Get PR status to check if PR exists and is open
                pr_info = ctx.github_ops.get_pr_status(repo_root, upstack_branch, debug=False)
                if pr_info.state != "OPEN":
                    continue

                if pr_info.pr_number is None:
                    continue

                pr_number = pr_info.pr_number

                # Check current base on GitHub
                current_base = ctx.github_ops.get_pr_base_branch(repo_root, pr_number)
                if current_base is None:
                    continue

                # Update base if stale
                if current_base != expected_parent:
                    if verbose or dry_run:
                        _emit(
                            f"  Updating PR #{pr_number} base: {current_base} → {expected_parent}",
                            script_mode=script_mode,
                        )
                    if dry_run:
                        edit_cmd = f"gh pr edit {pr_number} --base {expected_parent}"
                        _emit(_format_cli_command(edit_cmd, check), script_mode=script_mode)
                    else:
                        ctx.github_ops.update_pr_base_branch(repo_root, pr_number, expected_parent)
                        edit_cmd = f"gh pr edit {pr_number} --base {expected_parent}"
                        _emit(_format_cli_command(edit_cmd, check), script_mode=script_mode)
                elif verbose:
                    _emit(
                        f"  PR #{pr_number} base already correct: {current_base}",
                        script_mode=script_mode,
                    )

    return merged_branches


def _cleanup_and_navigate(
    ctx: WorkstackContext,
    repo_root: Path,
    merged_branches: list[str],
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> str:
    """Clean up merged worktrees and navigate to appropriate branch.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        merged_branches: List of successfully merged branch names
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        Name of branch after cleanup and navigation
    """
    check = click.style("✓", fg="green")

    # Print section header
    _emit("", script_mode=script_mode)
    _emit("Cleaning up...", script_mode=script_mode)

    # Get last merged branch to find next unmerged child
    last_merged = merged_branches[-1] if merged_branches else None

    # Step 0: Switch to root worktree before cleanup
    # This prevents shell from being left in a destroyed worktree directory
    # Pattern mirrors sync.py:123-125
    if ctx.cwd.resolve() != repo_root:
        try:
            os.chdir(repo_root)
            ctx = regenerate_context(ctx, repo_root=repo_root)
        except (FileNotFoundError, OSError):
            # Sentinel path in pure test mode - skip chdir
            pass

    # Step 1: Checkout main
    if not dry_run:
        ctx.git_ops.checkout_branch(repo_root, "main")
    _emit(_format_cli_command("git checkout main", check), script_mode=script_mode)
    final_branch = "main"

    # Step 2: Sync worktrees
    base_cmd = "workstack sync -f"
    if verbose:
        base_cmd += " --verbose"

    if dry_run:
        _emit(_format_cli_command(base_cmd, check), script_mode=script_mode)
    else:
        try:
            # This will remove merged worktrees and delete branches
            cmd = ["workstack", "sync", "-f"]
            if verbose:
                cmd.append("--verbose")

            subprocess.run(
                cmd,
                cwd=repo_root,
                check=True,
                capture_output=not verbose,
                text=True,
            )
            _emit(_format_cli_command(base_cmd, check), script_mode=script_mode)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            _emit(f"Warning: Cleanup sync failed: {error_msg}", script_mode=script_mode, error=True)

    # Step 3: Navigate to next branch or stay on main
    # Check if last merged branch had unmerged children
    if last_merged:
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
        if last_merged in all_branches:
            children = all_branches[last_merged].children or []
            # Check if any children still exist and are unmerged
            for child in children:
                if child in all_branches:
                    if not dry_run:
                        try:
                            ctx.git_ops.checkout_branch(repo_root, child)
                            cmd = _format_cli_command(f"git checkout {child}", check)
                            _emit(cmd, script_mode=script_mode)
                            final_branch = child
                            return final_branch
                        except Exception:
                            pass  # Child branch may have been deleted
                    else:
                        cmd = _format_cli_command(f"git checkout {child}", check)
                        _emit(cmd, script_mode=script_mode)
                        final_branch = child
                        return final_branch

    # No unmerged children, stay on main (already checked out above)
    return final_branch


def _show_final_state(
    merged_branches: list[str],
    final_branch: str,
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Display final state after landing operations.

    Args:
        merged_branches: List of successfully merged branch names
        final_branch: Name of current branch after all operations
        dry_run: If True, this was a dry run
        script_mode: True when running in --script mode (output to stderr)
    """
    _emit("Final state:", script_mode=script_mode)
    _emit("", script_mode=script_mode)

    # Success message
    pr_text = "PR" if len(merged_branches) == 1 else "PRs"
    success_msg = f"✅ Successfully landed {len(merged_branches)} {pr_text}"
    if dry_run:
        success_msg += click.style(" (dry run)", fg="bright_black")
    _emit(f"  {success_msg}", script_mode=script_mode)

    # Current branch
    branch_styled = click.style(final_branch, fg="yellow")
    _emit(f"  Current branch: {branch_styled}", script_mode=script_mode)

    # Merged branches
    branches_list = ", ".join(click.style(b, fg="yellow") for b in merged_branches)
    _emit(f"  Merged branches: {branches_list}", script_mode=script_mode)

    # Worktrees status
    _emit("  Worktrees: cleaned up", script_mode=script_mode)


@click.command("land-stack")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt and proceed immediately.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed output for merge and sync operations.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without executing merge operations.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.pass_obj
def land_stack(
    ctx: WorkstackContext, force: bool, verbose: bool, dry_run: bool, script: bool
) -> None:
    """Land all PRs from bottom of stack up to and including current branch.

    This command merges all PRs sequentially from the bottom of the stack (first
    branch above trunk) up to the current branch, running 'gt sync -f' between
    each merge to restack remaining branches.

    PRs are landed bottom-up because each PR depends on the ones below it.

    Requirements:
    - Graphite must be enabled (use-graphite config)
    - Clean working directory (no uncommitted changes)
    - All branches must have open PRs
    - Current branch must not be a trunk branch

    Example:
        Stack: main → feat-1 → feat-2 → feat-3
        Current branch: feat-3 (at top)
        Result: Lands feat-1, feat-2, feat-3 (in that order, bottom to top)
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = ctx.git_ops.get_current_branch(ctx.cwd)

    # Get branches to land
    branches_to_land = _get_branches_to_land(ctx, repo.root, current_branch or "")

    # Validate preconditions
    _validate_landing_preconditions(
        ctx, repo.root, current_branch, branches_to_land, script_mode=script
    )

    # Validate all branches have open PRs
    valid_branches = _validate_branches_have_prs(
        ctx, repo.root, branches_to_land, script_mode=script
    )

    # Validate no merge conflicts
    _validate_pr_mergeability(ctx, repo.root, valid_branches, script_mode=script)

    # Get trunk branch (parent of first branch to land)
    if not valid_branches:
        _emit("No branches to land.", script_mode=script, error=True)
        raise SystemExit(1)

    first_branch = valid_branches[0][0]  # First tuple is (branch, pr_number, title)
    trunk_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo.root, first_branch)
    if trunk_branch is None:
        error_msg = f"Error: Could not determine trunk branch for {first_branch}"
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1)

    # Show plan and get confirmation
    _show_landing_plan(
        current_branch or "",
        trunk_branch,
        valid_branches,
        force=force,
        dry_run=dry_run,
        script_mode=script,
    )

    # Execute landing sequence
    try:
        merged_branches = _land_branch_sequence(
            ctx, repo.root, valid_branches, verbose=verbose, dry_run=dry_run, script_mode=script
        )
    except subprocess.CalledProcessError as e:
        _emit("", script_mode=script)
        # Show full stderr from subprocess for complete error context
        error_detail = e.stderr.strip() if e.stderr else str(e)
        error_msg = click.style(f"❌ Landing stopped: {error_detail}", fg="red")
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1) from None
    except FileNotFoundError as e:
        _emit("", script_mode=script)
        error_msg = click.style(
            f"❌ Command not found: {e.filename}\n\n"
            "Install required tools:\n"
            "  • GitHub CLI: brew install gh\n"
            "  • Graphite CLI: brew install withgraphite/tap/graphite",
            fg="red",
        )
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1) from None

    # All succeeded - run cleanup operations
    final_branch = _cleanup_and_navigate(
        ctx, repo.root, merged_branches, verbose=verbose, dry_run=dry_run, script_mode=script
    )

    # Show final state
    _emit("", script_mode=script)
    _show_final_state(merged_branches, final_branch, dry_run=dry_run, script_mode=script)
