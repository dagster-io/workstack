from pathlib import Path

import click
from erk_shared.github.types import PullRequestInfo, WorkflowRun
from erk_shared.impl_folder import get_impl_path

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_branch_without_worktree,
    format_pr_info,
    format_workflow_status,
    format_worktree_line,
    get_visible_length,
)
from erk.core.file_utils import extract_plan_title
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_utils import find_current_worktree


def _format_plan_summary(worktree_path: Path, ctx: ErkContext) -> str | None:
    """Extract plan title from .impl/plan.md if it exists.

    Args:
        worktree_path: Path to the worktree directory
        ctx: Erk context with git operations

    Returns:
        Plan title string, or None if no plan file
    """
    # Check for new .impl/ folder format only
    plan_path = get_impl_path(worktree_path, git_ops=ctx.git)
    if plan_path is None:
        return None

    return extract_plan_title(plan_path, git_ops=ctx.git)


def _list_worktrees(ctx: ErkContext, ci: bool) -> None:
    """List worktrees with comprehensive branch information.

    Shows three sections:
    1. Worktrees (with PR info and plan summaries)
    2. Graphite branches without worktrees
    3. Local branches without worktrees
    """
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        # Discover repository context (handles None and NoRepoSentinel)
        # If not in a git repo, FileNotFoundError will bubble up
        repo = discover_repo_context(ctx, ctx.cwd)

    current_dir = ctx.cwd

    # Get branch info for all worktrees
    worktrees = ctx.git.list_worktrees(repo.root)
    branches = {wt.path: wt.branch for wt in worktrees}

    # Determine which worktree the user is currently in
    wt_info = find_current_worktree(worktrees, current_dir)
    current_worktree_path = wt_info.path if wt_info is not None else None

    # Fetch PR information based on config and flags
    prs: dict[str, PullRequestInfo] | None = None
    if ctx.global_config and ctx.global_config.show_pr_info:
        # Always try Graphite first (fast, no pagination issues)
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo.root)

        # Fail fast if Graphite cache unavailable
        if not prs:
            user_output(click.style("❌ Graphite PR cache not found", fg="red"))
            user_output()
            user_output("Erk requires Graphite PR data to list worktrees.")
            user_output()
            user_output(click.style("Run: ", fg="white") + click.style("gt sync", fg="yellow"))
            user_output()
            user_output(
                click.style("This will populate the Graphite cache at: ", fg="white")
                + click.style(".git/.graphite_pr_info", fg="cyan")
            )
            raise SystemExit(1)

        # Always fetch PR titles (lighter weight than full CI enrichment)
        prs = ctx.github.fetch_pr_titles_batch(prs, repo.root)

        # If --ci flag set, enrich with CI status and mergeability using batched GraphQL query
        if ci:
            prs = ctx.github.enrich_prs_with_ci_status_batch(prs, repo.root)

    # Fetch workflow run information using direct API queries
    # Build branch-to-worktree mapping for batch query
    branch_to_worktree: dict[str, Path] = {}
    for wt in worktrees:
        if wt.branch is not None:
            branch_to_worktree[wt.branch] = wt.path

    # Batch query workflow runs for all branches
    runs_by_branch: dict[str, WorkflowRun | None] = {}
    if branch_to_worktree:
        branch_names = list(branch_to_worktree.keys())
        try:
            runs_by_branch = ctx.github.get_workflow_runs_by_branches(
                repo.root, "dispatch-erk-queue.yml", branch_names
            )
        except Exception:
            # If API query fails, continue without workflow runs
            pass

    # Determine GitHub owner/repo from PR info for URL construction
    github_owner: str | None = None
    github_repo: str | None = None
    if prs:
        # Use first PR to extract owner/repo
        for pr in prs.values():
            github_owner = pr.owner
            github_repo = pr.repo
            break

    # Build worktree path -> (workflow run, url) mapping
    workflow_info: dict[Path, tuple[WorkflowRun | None, str | None]] = {}
    for branch, wt_path in branch_to_worktree.items():
        workflow_run = runs_by_branch.get(branch)
        workflow_url = None
        if workflow_run is not None and github_owner and github_repo:
            workflow_url = f"https://github.com/{github_owner}/{github_repo}/actions/runs/{workflow_run.run_id}"
        workflow_info[wt_path] = (workflow_run, workflow_url)

    # Add None entries for worktrees without branches or workflow runs
    for wt in worktrees:
        if wt.path not in workflow_info:
            workflow_info[wt.path] = (None, None)

    # Identify branches without worktrees
    branches_with_worktrees = {wt.branch for wt in worktrees if wt.branch is not None}

    # Get Graphite-tracked branches without worktrees
    all_graphite_branches = ctx.graphite.get_all_branches(ctx.git, repo.root)
    graphite_without_worktrees = [
        branch
        for branch in all_graphite_branches.keys()
        if branch not in branches_with_worktrees and not all_graphite_branches[branch].is_trunk
    ]

    # Get all local branches without worktrees (excluding Graphite-tracked ones)
    all_local_branches = ctx.git.list_local_branches(repo.root)
    local_without_worktrees = [
        branch
        for branch in all_local_branches
        if branch not in all_graphite_branches and branch not in branches_with_worktrees
    ]

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Calculate maximum widths for alignment
    # First, collect all names, branches, PR info, and workflow status to display
    # Start with root
    all_names = ["root"]
    all_branches = []
    all_pr_info = []
    all_workflow_status = []

    root_branch = branches.get(repo.root)
    if root_branch:
        branch_display = "=" if "root" == root_branch else root_branch
        all_branches.append(f"({branch_display})")

        # Add root PR info for width calculation
        if prs:
            pr = prs.get(root_branch)
            if pr:
                graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number)
                root_pr_info = format_pr_info(pr, graphite_url, use_graphite=use_graphite)
                all_pr_info.append(root_pr_info if root_pr_info else "[no PR]")
            else:
                all_pr_info.append("[no PR]")
        else:
            all_pr_info.append("[no PR]")

        # Add root workflow status for width calculation
        root_workflow_run, root_workflow_url = workflow_info.get(repo.root, (None, None))
        root_workflow_status = format_workflow_status(root_workflow_run, root_workflow_url)
        if root_workflow_status:
            all_workflow_status.append(root_workflow_status)
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
                    graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number)
                    wt_pr_info = format_pr_info(pr, graphite_url, use_graphite=use_graphite)
                    all_pr_info.append(wt_pr_info if wt_pr_info else "[no PR]")
                else:
                    all_pr_info.append("[no PR]")
            else:
                all_pr_info.append("[no PR]")

            # Add workflow status for width calculation
            wt_workflow_run, wt_workflow_url = workflow_info.get(wt.path, (None, None))
            wt_workflow_status = format_workflow_status(wt_workflow_run, wt_workflow_url)
            if wt_workflow_status:
                all_workflow_status.append(wt_workflow_status)
        else:
            all_pr_info.append("[no PR]")

    # Calculate max widths using visible length for PR info and workflow status
    max_name_len = max(len(name) for name in all_names) if all_names else 0
    max_branch_len = max(len(branch) for branch in all_branches) if all_branches else 0
    max_pr_info_len = (
        max(get_visible_length(pr_info) for pr_info in all_pr_info) if all_pr_info else 0
    )
    max_workflow_len = (
        max(get_visible_length(status) for status in all_workflow_status)
        if all_workflow_status
        else 0
    )

    # Section 1: Worktrees
    user_output(click.style("## Worktrees", bold=True))
    user_output()

    # Show root repo first (display as "root" to distinguish from worktrees)
    is_current_root = repo.root == current_worktree_path

    # Get PR info, workflow info, and plan summary for root
    root_pr_info = None
    root_pr_title = None
    if prs and root_branch:
        pr = prs.get(root_branch)
        if pr:
            graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number)
            root_pr_info = format_pr_info(pr, graphite_url, use_graphite=use_graphite)
            root_pr_title = pr.title
    root_plan_summary = _format_plan_summary(repo.root, ctx)

    # Get workflow info for root
    root_workflow_run, root_workflow_url = workflow_info.get(repo.root, (None, None))

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
            pr_title=root_pr_title,
            workflow_run=root_workflow_run,
            workflow_url=root_workflow_url,
            max_workflow_len=max_workflow_len,
        )
    )

    # Show worktrees - iterate over worktrees instead of filesystem
    for wt in non_root_worktrees:
        name = wt.path.name
        wt_path = wt.path
        wt_branch = wt.branch

        is_current_wt = wt_path == current_worktree_path

        # Get PR info, workflow info, and plan summary for this worktree
        wt_pr_info = None
        wt_pr_title = None
        if prs and wt_branch:
            pr = prs.get(wt_branch)
            if pr:
                graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number)
                wt_pr_info = format_pr_info(pr, graphite_url, use_graphite=use_graphite)
                wt_pr_title = pr.title
        wt_plan_summary = _format_plan_summary(wt_path, ctx)

        # Get workflow info for this worktree
        wt_workflow_run, wt_workflow_url = workflow_info.get(wt_path, (None, None))

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
                pr_title=wt_pr_title,
                workflow_run=wt_workflow_run,
                workflow_url=wt_workflow_url,
                max_workflow_len=max_workflow_len,
            )
        )

    # Section 2: Graphite branches without worktrees
    if graphite_without_worktrees:
        # Calculate max widths for alignment (same pattern as worktrees section)
        graphite_branch_names: list[str] = []
        graphite_pr_info_list: list[str] = []

        for branch in sorted(graphite_without_worktrees):
            graphite_branch_names.append(branch)

            # Get PR info for this branch
            branch_pr_info = None
            if prs:
                pr = prs.get(branch)
                if pr:
                    graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number)
                    branch_pr_info = format_pr_info(pr, graphite_url, use_graphite=use_graphite)

            if branch_pr_info:
                graphite_pr_info_list.append(branch_pr_info)
            else:
                graphite_pr_info_list.append("")

        # Calculate max widths using visible length for PR info
        max_graphite_branch_len = (
            max(len(branch) for branch in graphite_branch_names) if graphite_branch_names else 0
        )
        max_graphite_pr_info_len = (
            max(get_visible_length(pr_info) for pr_info in graphite_pr_info_list if pr_info)
            if any(graphite_pr_info_list)
            else 0
        )

        user_output()
        user_output(click.style("## Graphite branches without worktrees", bold=True))
        user_output()

        # Now iterate again to print with alignment
        for i, branch in enumerate(sorted(graphite_without_worktrees)):
            branch_pr_info = graphite_pr_info_list[i] if graphite_pr_info_list[i] else None
            user_output(
                format_branch_without_worktree(
                    branch,
                    branch_pr_info,
                    max_branch_len=max_graphite_branch_len,
                    max_pr_info_len=max_graphite_pr_info_len,
                )
            )

    # Section 3: Local branches without worktrees
    if local_without_worktrees:
        user_output()
        user_output(click.style("## Local branches without worktrees", bold=True))
        user_output()
        for branch in sorted(local_without_worktrees):
            user_output(click.style(branch, fg="yellow"))


@click.command("list")
@click.option("--ci", is_flag=True, help="Fetch CI check status from GitHub (slower)")
@click.pass_obj
def list_wt(ctx: ErkContext, ci: bool) -> None:
    """List worktrees with comprehensive branch and PR information.

    Shows three sections:
    1. Worktrees with their branches, PR status, and plans
    2. Graphite-tracked branches without worktrees
    3. Local branches without worktrees
    """
    _list_worktrees(ctx, ci=ci)


# Register ls as a hidden alias (won't show in help)
@click.command("ls", hidden=True)
@click.option("--ci", is_flag=True, help="Fetch CI check status from GitHub (slower)")
@click.pass_obj
def ls_wt(ctx: ErkContext, ci: bool) -> None:
    """List worktrees with comprehensive branch and PR information (alias of 'list')."""
    _list_worktrees(ctx, ci=ci)
