from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.display_utils import (
    filter_stack_for_worktree,
    format_pr_info,
    format_worktree_line,
    get_visible_length,
)
from workstack.core.github_ops import PullRequestInfo
from workstack.core.repo_discovery import RepoContext
from workstack.core.worktree_utils import find_current_worktree


def _format_plan_summary(worktree_path: Path, ctx: WorkstackContext) -> str | None:
    """Extract plan title from .plan/plan.md if it exists.

    Args:
        worktree_path: Path to the worktree directory
        ctx: Workstack context with git operations

    Returns:
        Plan title string, or None if no plan file
    """
    from workstack.core.file_utils import extract_plan_title
    from workstack.core.plan_folder import get_plan_path

    # Check for new .plan/ folder format only
    plan_path = get_plan_path(worktree_path, git_ops=ctx.git_ops)
    if plan_path is None:
        return None

    return extract_plan_title(plan_path, git_ops=ctx.git_ops)


def _display_branch_stack(
    ctx: WorkstackContext,
    repo_root: Path,
    worktree_path: Path,
    branch: str,
    all_branches: dict[Path, str | None],
    is_root_worktree: bool,
    prs: dict[str, PullRequestInfo] | None = None,  # If None, no PR info displayed
) -> None:
    """Display the graphite stack for a worktree with colorization and PR info.

    Shows branches with colored markers indicating which is currently checked out.
    Current branch is emphasized with bright green, others are de-emphasized with gray.
    Also displays PR status and links for branches that have PRs.

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to the repository root
        worktree_path: Path to the current worktree
        branch: Branch name to display stack for
        all_branches: Mapping of all worktree paths to their checked-out branches
        prs: Mapping of branch names to PR information (if None, no PR info displayed)
    """
    stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, branch)
    if not stack:
        return

    # Get current branch for filtering
    current_branch = all_branches.get(worktree_path)
    if current_branch is None:
        return

    # Build set of all checked-out branches
    all_checked_out_branches = {b for b in all_branches.values() if b is not None}

    filtered_stack = filter_stack_for_worktree(
        stack, current_branch, all_checked_out_branches, is_root_worktree
    )
    if not filtered_stack:
        return

    # Determine which branch to highlight
    actual_branch = ctx.git_ops.get_current_branch(worktree_path)
    highlight_branch = actual_branch if actual_branch else branch

    # Display stack with colored markers and PR info
    for branch_name in reversed(filtered_stack):
        is_current = branch_name == highlight_branch

        if is_current:
            # Current branch: bright green marker + bright green bold text
            marker = click.style("◉", fg="bright_green")
            branch_text = click.style(branch_name, fg="bright_green", bold=True)
        else:
            # Other branches: gray marker + normal text
            marker = click.style("◯", fg="bright_black")
            branch_text = branch_name  # Normal white text

        # Add PR info if available
        if prs:
            pr = prs.get(branch_name)
            if pr:
                graphite_url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)
                pr_info = format_pr_info(pr, graphite_url)
                line = f"  {marker}  {branch_text} {pr_info}"
            else:
                line = f"  {marker}  {branch_text}"
        else:
            line = f"  {marker}  {branch_text}"

        user_output(line)


def _list_worktrees(ctx: WorkstackContext, show_stacks: bool, ci: bool) -> None:
    """Internal function to list worktrees."""
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        # Discover repository context (handles None and NoRepoSentinel)
        # If not in a git repo, FileNotFoundError will bubble up
        repo = discover_repo_context(ctx, ctx.cwd)

    current_dir = ctx.cwd

    # Get branch info for all worktrees
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    branches = {wt.path: wt.branch for wt in worktrees}

    # Determine which worktree the user is currently in
    wt_info = find_current_worktree(worktrees, current_dir)
    current_worktree_path = wt_info.path if wt_info is not None else None

    # Validate graphite is enabled if showing stacks
    if show_stacks:
        if not (ctx.global_config and ctx.global_config.use_graphite):
            user_output(
                "Error: --stacks requires graphite to be enabled. "
                "Run 'workstack config set use_graphite true'",
            )
            raise SystemExit(1)

    # Fetch PR information based on config and flags
    prs: dict[str, PullRequestInfo] | None = None
    if ctx.global_config and ctx.global_config.show_pr_info:
        # Always try Graphite first (fast, no pagination issues)
        prs = ctx.graphite_ops.get_prs_from_graphite(ctx.git_ops, repo.root)

        # Fail fast if Graphite cache unavailable
        if not prs:
            user_output(click.style("❌ Graphite PR cache not found", fg="red"))
            user_output()
            user_output("Workstack requires Graphite PR data to list worktrees.")
            user_output()
            user_output(click.style("Run: ", fg="white") + click.style("gt sync", fg="yellow"))
            user_output()
            user_output(
                click.style("This will populate the Graphite cache at: ", fg="white")
                + click.style(".git/.graphite_pr_info", fg="cyan")
            )
            raise SystemExit(1)

        # If --ci flag set, enrich with CI status (slower, opt-in)
        if ci:
            prs = ctx.github_ops.enrich_prs_with_ci_status(prs, repo.root)

    # Calculate maximum widths for alignment
    # First, collect all names, branches, and PR info to display
    # Start with root
    all_names = ["root"]
    all_branches = []
    all_pr_info = []

    root_branch = branches.get(repo.root)
    if root_branch:
        branch_display = "=" if "root" == root_branch else root_branch
        all_branches.append(f"({branch_display})")

        # Add root PR info for width calculation
        if prs:
            pr = prs.get(root_branch)
            if pr:
                graphite_url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)
                root_pr_info = format_pr_info(pr, graphite_url)
                all_pr_info.append(root_pr_info if root_pr_info else "[no PR]")
            else:
                all_pr_info.append("[no PR]")
        else:
            all_pr_info.append("[no PR]")
    else:
        all_pr_info.append("[no PR]")

    # Add worktree entries - iterate over worktrees instead of filesystem
    # Filter out root worktree by comparing paths
    non_root_worktrees = [wt for wt in worktrees if wt.path != repo.root]
    for wt in sorted(non_root_worktrees, key=lambda w: w.path.name):
        name = wt.path.name
        branch_name = wt.branch
        all_names.append(name)
        if branch_name:
            branch_display = "=" if name == branch_name else branch_name
            all_branches.append(f"({branch_display})")

            # Add PR info for width calculation
            if prs:
                pr = prs.get(branch_name)
                if pr:
                    graphite_url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)
                    wt_pr_info = format_pr_info(pr, graphite_url)
                    all_pr_info.append(wt_pr_info if wt_pr_info else "[no PR]")
                else:
                    all_pr_info.append("[no PR]")
            else:
                all_pr_info.append("[no PR]")
        else:
            all_pr_info.append("[no PR]")

    # Calculate max widths using visible length for PR info
    max_name_len = max(len(name) for name in all_names) if all_names else 0
    max_branch_len = max(len(branch) for branch in all_branches) if all_branches else 0
    max_pr_info_len = (
        max(get_visible_length(pr_info) for pr_info in all_pr_info) if all_pr_info else 0
    )

    # Show root repo first (display as "root" to distinguish from worktrees)
    is_current_root = repo.root == current_worktree_path

    # Get PR info and plan summary for root
    root_pr_info = None
    if prs and root_branch:
        pr = prs.get(root_branch)
        if pr:
            graphite_url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)
            root_pr_info = format_pr_info(pr, graphite_url)
    root_plan_summary = _format_plan_summary(repo.root, ctx)

    user_output(
        format_worktree_line(
            "root",
            root_branch,
            pr_info=root_pr_info,
            plan_summary=root_plan_summary,
            is_root=True,
            is_current=is_current_root,
            max_name_len=max_name_len,
            max_branch_len=max_branch_len,
            max_pr_info_len=max_pr_info_len,
        )
    )

    if show_stacks and root_branch:
        _display_branch_stack(ctx, repo.root, repo.root, root_branch, branches, True, prs)

    # Show worktrees - iterate over worktrees instead of filesystem
    for idx, wt in enumerate(non_root_worktrees):
        name = wt.path.name
        wt_path = wt.path
        wt_branch = wt.branch

        # Add blank line before each worktree (except first) when showing stacks
        if show_stacks and (root_branch or idx > 0):
            user_output()

        is_current_wt = wt_path == current_worktree_path

        # Get PR info and plan summary for this worktree
        wt_pr_info = None
        if prs and wt_branch:
            pr = prs.get(wt_branch)
            if pr:
                graphite_url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)
                wt_pr_info = format_pr_info(pr, graphite_url)
        wt_plan_summary = _format_plan_summary(wt_path, ctx)

        user_output(
            format_worktree_line(
                name,
                wt_branch,
                pr_info=wt_pr_info,
                plan_summary=wt_plan_summary,
                is_root=False,
                is_current=is_current_wt,
                max_name_len=max_name_len,
                max_branch_len=max_branch_len,
                max_pr_info_len=max_pr_info_len,
            )
        )

        if show_stacks and wt_branch:
            _display_branch_stack(ctx, repo.root, wt_path, wt_branch, branches, False, prs)


@click.command("list")
@click.option("--stacks", "-s", is_flag=True, help="Show graphite stacks for each worktree")
@click.option("--ci", is_flag=True, help="Fetch CI check status from GitHub (slower)")
@click.pass_obj
def list_cmd(ctx: WorkstackContext, stacks: bool, ci: bool) -> None:
    """List worktrees with branches, PR status, and plans."""
    _list_worktrees(ctx, show_stacks=stacks, ci=ci)


# Register ls as a hidden alias (won't show in help)
@click.command("ls", hidden=True)
@click.option("--stacks", "-s", is_flag=True, help="Show graphite stacks for each worktree")
@click.option("--ci", is_flag=True, help="Fetch CI check status from GitHub (slower)")
@click.pass_obj
def ls_cmd(ctx: WorkstackContext, stacks: bool, ci: bool) -> None:
    """List worktrees with branches, PR status, and plans (alias of 'list')."""
    _list_worktrees(ctx, show_stacks=stacks, ci=ci)
