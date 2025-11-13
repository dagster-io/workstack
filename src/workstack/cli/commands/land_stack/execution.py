"""Core landing sequence execution for land-stack command."""

import subprocess
from pathlib import Path

import click

from workstack.cli.commands.land_stack.discovery import _get_all_children
from workstack.cli.commands.land_stack.models import BranchPR
from workstack.cli.commands.land_stack.output import _emit, _format_cli_command, _format_description
from workstack.core.context import WorkstackContext


def _land_branch_sequence(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[BranchPR],
    *,
    verbose: bool,
    dry_run: bool,
    down_only: bool,
    script_mode: bool,
) -> list[str]:
    """Land branches sequentially, one at a time with restack between each.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branches: List of BranchPR to land
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        down_only: If True, skip upstack rebase and force-push operations
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

        # Phase 3.5: Sync trunk with remote
        # At this point, parent should be trunk (verified in Phase 2)
        if parent is None:
            raise RuntimeError(f"Cannot sync trunk: {branch} has no parent branch")

        if dry_run:
            _emit(_format_cli_command(f"git fetch origin {parent}", check), script_mode=script_mode)
            _emit(_format_cli_command(f"git checkout {parent}", check), script_mode=script_mode)
            _emit(
                _format_cli_command(f"git pull --ff-only origin {parent}", check),
                script_mode=script_mode,
            )
            _emit(_format_cli_command(f"git checkout {branch}", check), script_mode=script_mode)
        else:
            # Sync trunk to include just-merged PR commits
            ctx.git_ops.fetch_branch(repo_root, "origin", parent)
            ctx.git_ops.checkout_branch(repo_root, parent)
            ctx.git_ops.pull_branch(repo_root, "origin", parent, ff_only=True)
            ctx.git_ops.checkout_branch(repo_root, branch)

            _emit(_format_cli_command(f"git fetch origin {parent}", check), script_mode=script_mode)
            _emit(_format_cli_command(f"git checkout {parent}", check), script_mode=script_mode)
            _emit(
                _format_cli_command(f"git pull --ff-only origin {parent}", check),
                script_mode=script_mode,
            )
            _emit(_format_cli_command(f"git checkout {branch}", check), script_mode=script_mode)

        # Phase 4: Restack (skip if down_only)
        if not down_only:
            if dry_run:
                _emit(_format_cli_command("gt sync -f", check), script_mode=script_mode)
            else:
                ctx.graphite_ops.sync(repo_root, force=True, quiet=not verbose)
                _emit(_format_cli_command("gt sync -f", check), script_mode=script_mode)

        # Phase 5: Force-push rebased branches (skip if down_only)
        # After gt sync -f rebases remaining branches locally,
        # push them to GitHub so subsequent PR merges will succeed
        #
        # Get ALL upstack branches from the full Graphite tree, not just
        # the branches in our landing list. After landing feat-1 in a stack
        # like main → feat-1 → feat-2 → feat-3, we need to force-push BOTH
        # feat-2 and feat-3, even if we're only landing up to feat-2.
        if not down_only:
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
                            ctx.graphite_ops.submit_branch(
                                repo_root, upstack_branch, quiet=not verbose
                            )
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
                            msg = (
                                f"  Updating PR #{pr_number} base: "
                                f"{current_base} → {expected_parent}"
                            )
                            _emit(msg, script_mode=script_mode)
                        if dry_run:
                            edit_cmd = f"gh pr edit {pr_number} --base {expected_parent}"
                            _emit(_format_cli_command(edit_cmd, check), script_mode=script_mode)
                        else:
                            ctx.github_ops.update_pr_base_branch(
                                repo_root, pr_number, expected_parent
                            )
                            edit_cmd = f"gh pr edit {pr_number} --base {expected_parent}"
                            _emit(_format_cli_command(edit_cmd, check), script_mode=script_mode)
                    elif verbose:
                        _emit(
                            f"  PR #{pr_number} base already correct: {current_base}",
                            script_mode=script_mode,
                        )

    return merged_branches
