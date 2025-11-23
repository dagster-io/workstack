from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.create import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.debug import debug_log
from erk.cli.output import machine_output, user_output
from erk.core.context import ErkContext, create_context
from erk.core.git.abc import WorktreeInfo
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir


class Ensure:
    """Helper class for asserting invariants with consistent error handling."""

    @staticmethod
    def truthy[T](value: T, error_message: str) -> T:
        """Ensure value is truthy, otherwise output error and exit.

        Args:
            value: Value to check for truthiness
            error_message: Error message to display if value is falsy

        Returns:
            The value unchanged if truthy

        Raises:
            SystemExit: If value is falsy (with exit code 1)
        """
        if not value:
            user_output(error_message)
            raise SystemExit(1)
        return value

    @staticmethod
    def invariant(condition: bool, error_message: str) -> None:
        """Ensure condition is true, otherwise output error and exit.

        Args:
            condition: Boolean condition to check
            error_message: Error message to display if condition is false

        Raises:
            SystemExit: If condition is false (with exit code 1)
        """
        if not condition:
            user_output(error_message)
            raise SystemExit(1)


def ensure_graphite_enabled(ctx: ErkContext) -> None:
    """Validate that Graphite is enabled.

    Args:
        ctx: Erk context

    Raises:
        SystemExit: If Graphite is not enabled
    """
    if not (ctx.global_config and ctx.global_config.use_graphite):
        user_output(
            "Error: This command requires Graphite to be enabled. "
            "Run 'erk config set use_graphite true'"
        )
        raise SystemExit(1)


def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    if ctx.git.has_uncommitted_changes(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red")
            + "Cannot delete current branch with uncommitted changes.\n"
            "Please commit or stash your changes first."
        )
        raise SystemExit(1)


def verify_pr_merged(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Verify that the branch's PR is merged on GitHub.

    Raises SystemExit if PR not found or not merged.
    """
    pr_info = ctx.github.get_pr_status(repo_root, branch, debug=False)

    if pr_info.state == "NONE" or pr_info.pr_number is None:
        user_output(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch}'.\n"
            "Cannot verify merge status."
        )
        raise SystemExit(1)

    if pr_info.state != "MERGED":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is not merged.\n"
            "Only merged branches can be deleted with --delete-current."
        )
        raise SystemExit(1)


def delete_branch_and_worktree(
    ctx: ErkContext, repo_root: Path, branch: str, worktree_path: Path
) -> None:
    """Delete the specified branch and its worktree.

    Uses two-step deletion: git worktree remove, then manual cleanup.
    """

    # Remove the worktree
    ctx.git.remove_worktree(repo_root, worktree_path, force=True)
    user_output(f"✓ Removed worktree: {click.style(str(worktree_path), fg='green')}")

    # Delete the branch using Git abstraction
    ctx.git.delete_branch_with_graphite(repo_root, branch, force=True)
    user_output(f"✓ Deleted branch: {click.style(branch, fg='yellow')}")

    # Prune worktree metadata
    ctx.git.prune_worktrees(repo_root)


def activate_root_repo(ctx: ErkContext, repo: RepoContext, script: bool, command_name: str) -> None:
    """Activate the root repository and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)

    Raises:
        SystemExit: Always (successful exit after activation)
    """
    root_path = repo.root
    if script:
        script_content = render_activation_script(
            worktree_path=root_path,
            final_message='echo "Switched to root repo: $(pwd)"',
            comment="work activate-script (root repo)",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name=command_name,
            comment="activate root",
        )
        machine_output(str(result.path), nl=False)
    else:
        user_output(f"Switched to root repo: {root_path}")
        user_output(
            "\nShell integration not detected. "
            "Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"Or use: source <(erk {command_name} --script)")
    raise SystemExit(0)


def activate_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
) -> None:
    """Activate a worktree and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)

    Raises:
        SystemExit: If worktree not found, or after successful activation
    """
    wt_path = target_path

    Ensure.invariant(ctx.git.path_exists(wt_path), f"Worktree not found: {wt_path}")

    worktree_name = wt_path.name

    if script:
        activation_script = render_activation_script(worktree_path=wt_path)
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=f"activate {worktree_name}",
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {result.path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {result.path.exists()}")

        result.output_for_shell_integration()
    else:
        user_output(
            "Shell integration not detected. Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"\nOr use: source <(erk {command_name} --script)")
    raise SystemExit(0)


def resolve_up_navigation(
    ctx: ErkContext, repo: RepoContext, current_branch: str, worktrees: list[WorktreeInfo]
) -> tuple[str, bool]:
    """Resolve --up navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at top of stack)
    """
    # Navigate up to child branch
    children = Ensure.truthy(
        ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch),
        "Already at the top of the stack (no child branches)",
    )

    # Fail explicitly if multiple children exist
    if len(children) > 1:
        children_list = ", ".join(f"'{child}'" for child in children)
        user_output(
            f"Error: Branch '{current_branch}' has multiple children: {children_list}.\n"
            f"Please create worktree for specific child: erk create <branch-name>"
        )
        raise SystemExit(1)

    # Use the single child
    target_branch = children[0]

    # Check if target branch has a worktree, create if necessary
    target_wt_path = ctx.git.find_worktree_for_branch(repo.root, target_branch)
    if target_wt_path is None:
        # Auto-create worktree for target branch
        _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, target_branch)
        return target_branch, was_created

    return target_branch, False


def resolve_down_navigation(
    ctx: ErkContext,
    repo: RepoContext,
    current_branch: str,
    worktrees: list[WorktreeInfo],
    trunk_branch: str | None,
) -> tuple[str, bool]:
    """Resolve --down navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()
        trunk_branch: Configured trunk branch name, or None for auto-detection

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name or 'root' to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at bottom of stack)
    """
    # Navigate down to parent branch
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is None:
        # Check if we're already on trunk
        detected_trunk = ctx.git.detect_default_branch(repo.root, trunk_branch)
        if current_branch == detected_trunk:
            user_output(f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')")
            raise SystemExit(1)
        else:
            user_output("Error: Could not determine parent branch from Graphite metadata")
            raise SystemExit(1)

    # Check if parent is the trunk - if so, switch to root
    detected_trunk = ctx.git.detect_default_branch(repo.root, trunk_branch)
    if parent_branch == detected_trunk:
        # Check if trunk is checked out in root (repo.root path)
        trunk_wt_path = ctx.git.find_worktree_for_branch(repo.root, detected_trunk)
        if trunk_wt_path is not None and trunk_wt_path == repo.root:
            # Trunk is in root repository, not in a dedicated worktree
            return "root", False
        else:
            # Trunk has a dedicated worktree
            if trunk_wt_path is None:
                # Auto-create worktree for trunk branch
                _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
                return parent_branch, was_created
            return parent_branch, False
    else:
        # Parent is not trunk, check if it has a worktree
        target_wt_path = ctx.git.find_worktree_for_branch(repo.root, parent_branch)
        if target_wt_path is None:
            # Auto-create worktree for parent branch
            _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
            return parent_branch, was_created
        return parent_branch, False


def complete_worktree_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for worktree names. Includes 'root' for the repository root.

    This is a shell completion function, which is an acceptable error boundary.
    Exceptions are caught to provide graceful degradation - if completion fails,
    we return an empty list rather than breaking the user's shell experience.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    try:
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

        repo = discover_repo_context(erk_ctx, erk_ctx.cwd)
        ensure_erk_metadata_dir(repo)

        names = ["root"] if "root".startswith(incomplete) else []

        # Get worktree names from git_ops instead of filesystem iteration
        worktrees = erk_ctx.git.list_worktrees(repo.root)
        for wt in worktrees:
            if wt.is_root:
                continue  # Skip root worktree (already added as "root")
            worktree_name = wt.path.name
            if worktree_name.startswith(incomplete):
                names.append(worktree_name)

        return names
    except Exception:
        # Shell completion error boundary: return empty list for graceful degradation
        return []


def complete_branch_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for branch names. Includes both local and remote branches.

    Remote branch names have their remote prefix stripped
    (e.g., 'origin/feature' becomes 'feature').
    Duplicates are removed if a branch exists both locally and remotely.

    This is a shell completion function, which is an acceptable error boundary.
    Exceptions are caught to provide graceful degradation - if completion fails,
    we return an empty list rather than breaking the user's shell experience.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    try:
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

        repo = discover_repo_context(erk_ctx, erk_ctx.cwd)
        ensure_erk_metadata_dir(repo)

        # Collect all branch names in a set for deduplication
        branch_names = set()

        # Add local branches
        local_branches = erk_ctx.git.list_local_branches(repo.root)
        branch_names.update(local_branches)

        # Add remote branches with prefix stripped
        remote_branches = erk_ctx.git.list_remote_branches(repo.root)
        for remote_branch in remote_branches:
            # Strip remote prefix (e.g., 'origin/feature' -> 'feature')
            if "/" in remote_branch:
                _, branch_name = remote_branch.split("/", 1)
                branch_names.add(branch_name)
            else:
                # Fallback: if no slash, use as-is
                branch_names.add(remote_branch)

        # Filter by incomplete prefix and return sorted list
        matching_branches = [name for name in branch_names if name.startswith(incomplete)]
        return sorted(matching_branches)
    except Exception:
        # Shell completion error boundary: return empty list for graceful degradation
        return []


def complete_plan_files(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for plan files (markdown files in current directory).

    This is a shell completion function, which is an acceptable error boundary.
    Exceptions are caught to provide graceful degradation - if completion fails,
    we return an empty list rather than breaking the user's shell experience.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete

    Returns:
        List of completion candidates (filenames matching incomplete text)
    """
    try:
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

        # Get current working directory from erk context
        cwd = erk_ctx.cwd

        # Find all .md files in current directory
        candidates = []
        for md_file in cwd.glob("*.md"):
            # Filter by incomplete prefix if provided
            if md_file.name.startswith(incomplete):
                candidates.append(md_file.name)

        return sorted(candidates)
    except Exception:
        # Shell completion error boundary: return empty list on any error
        # This ensures shell doesn't show Python tracebacks during tab-completion
        return []
