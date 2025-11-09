from pathlib import Path

import click

from workstack.cli.core import discover_repo_context, ensure_workstacks_dir
from workstack.core.context import WorkstackContext
from workstack.core.github_ops import PullRequestInfo


def _get_visible_length(text: str) -> int:
    """Calculate the visible length of text, excluding ANSI and OSC escape sequences.

    Args:
        text: Text that may contain escape sequences

    Returns:
        Number of visible characters
    """
    import re

    # Remove ANSI color codes (\033[...m)
    text = re.sub(r"\033\[[0-9;]*m", "", text)
    # Remove OSC 8 hyperlink sequences (\033]8;;URL\033\\)
    text = re.sub(r"\033\]8;;[^\033]*\033\\", "", text)
    return len(text)


def _format_worktree_line(
    name: str,
    branch: str | None,
    pr_info: str | None,
    plan_summary: str | None,
    is_root: bool,
    is_current: bool,
    max_name_len: int = 0,
    max_branch_len: int = 0,
    max_pr_info_len: int = 0,
) -> str:
    """Format a single worktree line with colorization and optional alignment.

    Args:
        name: Worktree name to display
        branch: Branch name (if any)
        pr_info: Formatted PR info string (e.g., "✅ #23") or None
        plan_summary: Plan title or None if no plan
        is_root: True if this is the root repository worktree
        is_current: True if this is the worktree the user is currently in
        max_name_len: Maximum name length for alignment (0 = no alignment)
        max_branch_len: Maximum branch length for alignment (0 = no alignment)
        max_pr_info_len: Maximum PR info visible length for alignment (0 = no alignment)

    Returns:
        Formatted line with colorization in format: name (branch) {PR info} {plan summary}
    """
    # Root worktree gets green to distinguish it from regular worktrees
    name_color = "green" if is_root else "cyan"

    # Calculate padding for name field
    name_padding = max_name_len - len(name) if max_name_len > 0 else 0
    name_with_padding = name + (" " * name_padding)
    name_part = click.style(name_with_padding, fg=name_color, bold=True)

    # Build parts for display: name (branch) {PR info} {plan summary}
    parts = [name_part]

    # Add branch in parentheses (yellow)
    # If name matches branch, show "=" instead of repeating the branch name
    if branch:
        branch_display = "=" if name == branch else branch
        # Calculate padding for branch field (including parentheses)
        branch_with_parens = f"({branch_display})"
        branch_padding = max_branch_len - len(branch_with_parens) if max_branch_len > 0 else 0
        branch_with_padding = branch_with_parens + (" " * branch_padding)
        branch_part = click.style(branch_with_padding, fg="yellow")
        parts.append(branch_part)
    elif max_branch_len > 0:
        # Add spacing even if no branch to maintain alignment
        parts.append(" " * max_branch_len)

    # Add PR info or placeholder with alignment
    pr_info_placeholder = click.style("[no PR]", fg="white", dim=True)
    pr_display = pr_info if pr_info else pr_info_placeholder

    if max_pr_info_len > 0:
        # Calculate visible length and add padding
        visible_len = _get_visible_length(pr_display)
        padding = max_pr_info_len - visible_len
        pr_display_with_padding = pr_display + (" " * padding)
        parts.append(pr_display_with_padding)
    else:
        parts.append(pr_display)

    # Add plan summary or placeholder
    if plan_summary:
        plan_colored = click.style(f"📋 {plan_summary}", fg="bright_magenta")
        parts.append(plan_colored)
    else:
        parts.append(click.style("[no plan]", fg="white", dim=True))

    # Build the main line
    line = " ".join(parts)

    # Add indicator on the right for current worktree
    if is_current:
        indicator = click.style(" ← (cwd)", fg="bright_blue")
        line += indicator

    return line


def _filter_stack_for_worktree(
    stack: list[str],
    current_worktree_path: Path,
    all_worktree_branches: dict[Path, str | None],
    is_root_worktree: bool,
) -> list[str]:
    """Filter a graphite stack to only show branches relevant to the current worktree.

    When displaying a stack for a specific worktree, we want to show:
    - Root worktree: Current branch + all ancestors (no descendants)
    - Other worktrees: Ancestors + current + descendants that are checked out somewhere

    This ensures that:
    - Root worktree shows context from trunk down to current branch
    - Other worktrees show full context but only "active" descendants with worktrees
    - Branches without active worktrees don't clutter non-root displays

    Example:
        Stack: [main, foo, bar, baz]
        Worktrees:
          - root on bar
          - worktree-baz on baz

        Root display: [main, foo, bar]  (ancestors + current, no descendants)
        Worktree-baz display: [main, foo, bar, baz]  (full context with checked-out descendants)

    Args:
        stack: The full graphite stack (ordered from trunk to leaf)
        current_worktree_path: Path to the worktree we're displaying the stack for
        all_worktree_branches: Mapping of all worktree paths to their checked-out branches
        is_root_worktree: True if this is the root repository worktree

    Returns:
        Filtered stack with only relevant branches
    """
    # Get the branch checked out in the current worktree
    current_branch = all_worktree_branches.get(current_worktree_path)
    if current_branch is None or current_branch not in stack:
        # If current branch is not in stack (shouldn't happen), return full stack
        return stack

    # Find the index of the current branch in the stack
    current_idx = stack.index(current_branch)

    # Filter the stack based on whether this is the root worktree
    if is_root_worktree:
        # Root worktree: show only ancestors + current (no descendants)
        # This keeps the display clean and focused on context
        return stack[: current_idx + 1]
    else:
        # Non-root worktree: show ancestors + current + descendants with worktrees
        # Build a set of branches that are checked out in ANY worktree
        all_checked_out_branches = {
            branch for branch in all_worktree_branches.values() if branch is not None
        }

        result = []
        for i, branch in enumerate(stack):
            if i <= current_idx:
                # Ancestors and current branch: always keep
                result.append(branch)
            else:
                # Descendants: only keep if checked out in some worktree
                if branch in all_checked_out_branches:
                    result.append(branch)

        return result


def _is_trunk_branch(ctx: WorkstackContext, repo_root: Path, branch: str) -> bool:
    """Check if a branch is a trunk branch (has no parent in graphite).

    Returns False for missing cache files rather than None because this function
    answers a boolean question: "Is this branch trunk?" When cache is missing,
    the answer is definitively "no" (we can't determine trunk status, default to False).

    This differs from get_branch_stack() which returns None for missing cache because
    it's retrieving optional data - None indicates "no stack data available" vs
    an empty list which would mean "stack exists but is empty".

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to the repository root
        branch: Branch name to check

    Returns:
        True if the branch is a trunk branch (no parent), False otherwise
        False is also returned when cache is missing/inaccessible (conservative default)
    """
    # Get all branches from GraphiteOps abstraction
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        return False

    # Check if branch exists and is trunk
    if branch in all_branches:
        return all_branches[branch].is_trunk

    return False


def _get_pr_status_emoji(pr: PullRequestInfo) -> str:
    """Determine the emoji to display for a PR based on its status.

    Args:
        pr: Pull request information

    Returns:
        Emoji character representing the PR's current state
    """
    if pr.is_draft:
        return "🚧"
    if pr.state == "MERGED":
        return "🟣"
    if pr.state == "CLOSED":
        return "⭕"
    if pr.checks_passing is True:
        return "✅"
    if pr.checks_passing is False:
        return "❌"
    # Open PR with no checks
    return "◯"


def _format_pr_info(
    ctx: WorkstackContext,
    repo_root: Path,
    branch: str,
    prs: dict[str, PullRequestInfo],
) -> str:
    """Format PR status indicator with emoji and link.

    Args:
        ctx: Workstack context with GitHub/Graphite operations
        repo_root: Repository root directory
        branch: Branch name
        prs: Mapping of branch name -> PullRequestInfo

    Returns:
        Formatted PR info string (e.g., "✅ #23") or empty string if no PR
    """
    pr = prs.get(branch)
    if pr is None:
        return ""

    emoji = _get_pr_status_emoji(pr)

    # Get Graphite URL (always available since we have owner/repo from GitHub)
    url = ctx.graphite_ops.get_graphite_url(pr.owner, pr.repo, pr.number)

    # Format as clickable link using OSC 8 terminal escape sequence with cyan color
    # Format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    pr_text = f"#{pr.number}"
    # Wrap the link text in cyan color to distinguish from non-clickable bright_blue indicators
    colored_pr_text = click.style(pr_text, fg="cyan")
    clickable_link = f"\033]8;;{url}\033\\{colored_pr_text}\033]8;;\033\\"

    return f"{emoji} {clickable_link}"


def _format_plan_summary(worktree_path: Path) -> str | None:
    """Extract plan title from .PLAN.md if it exists.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        Plan title string, or None if no plan file
    """
    from workstack.core.file_utils import extract_plan_title

    plan_path = worktree_path / ".PLAN.md"
    return extract_plan_title(plan_path)


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

    filtered_stack = _filter_stack_for_worktree(
        stack, worktree_path, all_branches, is_root_worktree
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
            pr_info = _format_pr_info(ctx, repo_root, branch_name, prs)
            if pr_info:
                line = f"  {marker}  {branch_text} {pr_info}"
            else:
                line = f"  {marker}  {branch_text}"
        else:
            line = f"  {marker}  {branch_text}"

        click.echo(line)


def _list_worktrees(ctx: WorkstackContext, show_stacks: bool, show_checks: bool) -> None:
    """Internal function to list worktrees."""
    repo = discover_repo_context(ctx, Path.cwd())
    current_dir = Path.cwd().resolve()

    # Get branch info for all worktrees
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    branches = {wt.path: wt.branch for wt in worktrees}

    # Determine which worktree the user is currently in
    current_worktree_path = None
    for wt_path in branches.keys():
        if wt_path.exists():
            wt_path_resolved = wt_path.resolve()
            if current_dir == wt_path_resolved or current_dir.is_relative_to(wt_path_resolved):
                current_worktree_path = wt_path_resolved
                break

    # Validate graphite is enabled if showing stacks
    if show_stacks:
        if not ctx.global_config_ops.get_use_graphite():
            click.echo(
                "Error: --stacks requires graphite to be enabled. "
                "Run 'workstack config set use_graphite true'",
                err=True,
            )
            raise SystemExit(1)

    # Fetch PR information based on config and flags
    prs: dict[str, PullRequestInfo] | None = None
    if ctx.global_config_ops.get_show_pr_info():
        # Determine if we need CI check status
        need_checks = show_checks or ctx.global_config_ops.get_show_pr_checks()

        if need_checks:
            # Fetch from GitHub with check status (slower)
            prs = ctx.github_ops.get_prs_for_repo(repo.root, include_checks=True)
        else:
            # Try Graphite first (fast - no CI status)
            prs = ctx.graphite_ops.get_prs_from_graphite(ctx.git_ops, repo.root)

            # If Graphite data not available, fall back to GitHub without checks
            if not prs:
                prs = ctx.github_ops.get_prs_for_repo(repo.root, include_checks=False)

    # Calculate maximum widths for alignment
    # First, collect all names, branches, and PR info to display
    workstacks_dir = ensure_workstacks_dir(repo)

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
            root_pr_info = _format_pr_info(ctx, repo.root, root_branch, prs)
            all_pr_info.append(root_pr_info if root_pr_info else "[no PR]")
        else:
            all_pr_info.append("[no PR]")
    else:
        all_pr_info.append("[no PR]")

    # Add worktree entries
    if workstacks_dir.exists():
        entries = sorted(p for p in workstacks_dir.iterdir() if p.is_dir())
        for p in entries:
            name = p.name
            # Check if this directory has a corresponding worktree
            for branch_path, branch_name in branches.items():
                if branch_path.resolve() == p.resolve():
                    all_names.append(name)
                    if branch_name:
                        branch_display = "=" if name == branch_name else branch_name
                        all_branches.append(f"({branch_display})")

                        # Add PR info for width calculation
                        if prs:
                            wt_pr_info = _format_pr_info(ctx, repo.root, branch_name, prs)
                            all_pr_info.append(wt_pr_info if wt_pr_info else "[no PR]")
                        else:
                            all_pr_info.append("[no PR]")
                    else:
                        all_pr_info.append("[no PR]")
                    break

    # Calculate max widths using visible length for PR info
    max_name_len = max(len(name) for name in all_names) if all_names else 0
    max_branch_len = max(len(branch) for branch in all_branches) if all_branches else 0
    max_pr_info_len = (
        max(_get_visible_length(pr_info) for pr_info in all_pr_info) if all_pr_info else 0
    )

    # Show root repo first (display as "root" to distinguish from worktrees)
    is_current_root = repo.root.resolve() == current_worktree_path

    # Get PR info and plan summary for root
    root_pr_info = None
    if prs and root_branch:
        root_pr_info = _format_pr_info(ctx, repo.root, root_branch, prs)
    root_plan_summary = _format_plan_summary(repo.root)

    click.echo(
        _format_worktree_line(
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

    # Show worktrees
    if not workstacks_dir.exists():
        return
    entries = sorted(p for p in workstacks_dir.iterdir() if p.is_dir())
    for p in entries:
        name = p.name
        # Find the actual worktree path from git worktree list
        # The path p might be a symlink or different from the actual worktree path
        wt_path = None
        wt_branch = None
        for branch_path, branch_name in branches.items():
            if branch_path.resolve() == p.resolve():
                wt_path = branch_path
                wt_branch = branch_name
                break

        # Skip directories that don't have a corresponding git worktree entry
        # (e.g., leftover empty directories after worktree removal)
        if wt_path is None:
            continue

        # Add blank line before each worktree (except first) when showing stacks
        if show_stacks and (root_branch or entries.index(p) > 0):
            click.echo()

        is_current_wt = bool(wt_path and wt_path.resolve() == current_worktree_path)

        # Get PR info and plan summary for this worktree
        wt_pr_info = None
        if prs and wt_branch:
            wt_pr_info = _format_pr_info(ctx, repo.root, wt_branch, prs)
        wt_plan_summary = _format_plan_summary(wt_path) if wt_path else None

        click.echo(
            _format_worktree_line(
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

        if show_stacks and wt_branch and wt_path:
            _display_branch_stack(ctx, repo.root, wt_path, wt_branch, branches, False, prs)


@click.command("list")
@click.option("--stacks", "-s", is_flag=True, help="Show graphite stacks for each worktree")
@click.option(
    "--checks", "-c", is_flag=True, help="Show CI check status (requires GitHub API call)"
)
@click.pass_obj
def list_cmd(ctx: WorkstackContext, stacks: bool, checks: bool) -> None:
    """List worktrees with activation hints (alias: ls)."""
    _list_worktrees(ctx, show_stacks=stacks, show_checks=checks)


# Register ls as a hidden alias (won't show in help)
@click.command("ls", hidden=True)
@click.option("--stacks", "-s", is_flag=True, help="Show graphite stacks for each worktree")
@click.option(
    "--checks", "-c", is_flag=True, help="Show CI check status (requires GitHub API call)"
)
@click.pass_obj
def ls_cmd(ctx: WorkstackContext, stacks: bool, checks: bool) -> None:
    """List worktrees with activation hints (alias of 'list')."""
    _list_worktrees(ctx, show_stacks=stacks, show_checks=checks)
