"""Command to create worktree from plan issue and invoke Claude implementation."""

import json

import click
from erk_shared.impl_folder import create_impl_folder
from erk_shared.naming import (
    ensure_unique_worktree_name_with_date,
    generate_filename_from_title,
    sanitize_worktree_name,
    strip_plan_from_filename,
)

from erk.cli.activation import render_activation_script
from erk.cli.commands.create import add_worktree, run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_issue_store.types import PlanIssueState
from erk.core.repo_discovery import ensure_erk_metadata_dir


def _build_claude_command(slash_command: str, dangerous: bool) -> str:
    """Build a Claude CLI invocation with appropriate flags.

    Args:
        slash_command: The slash command to execute (e.g., "/erk:implement-plan")
        dangerous: Whether to skip permission prompts

    Returns:
        Complete Claude CLI command string
    """
    cmd = "claude --permission-mode acceptEdits"
    if dangerous:
        cmd += " --dangerously-skip-permissions"
    cmd += f' "{slash_command}"'
    return cmd


def _generate_worktree_name_from_title(ctx: ErkContext, title: str) -> str:
    """Generate worktree name from plan issue title.

    Args:
        ctx: Erk context
        title: Plan issue title

    Returns:
        Generated filename stem (without extension)
    """
    # Convert title to filename directly (no subprocess)
    filename = generate_filename_from_title(title)

    # Remove extension and "-plan" suffix to get worktree name
    # "my-feature-plan.md" -> "my-feature-plan" -> "my-feature"
    stem = filename.removesuffix(".md")
    name = strip_plan_from_filename(stem)

    return name


@click.command("implement")
@click.argument("issue_number", type=int)
@click.option(
    "--worktree-name",
    type=str,
    default=None,
    help="Override worktree name (optional, auto-generated from issue title if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be executed without doing it",
)
@click.option(
    "--dangerous",
    is_flag=True,
    default=False,
    help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output activation script for shell integration",
)
@click.pass_obj
def implement_plan_issue(
    ctx: ErkContext,
    issue_number: int,
    worktree_name: str | None,
    dry_run: bool,
    dangerous: bool,
    script: bool,
) -> None:
    """Create worktree from plan issue and invoke Claude for implementation.

    This command combines worktree creation with automatic Claude invocation:
    1. Fetches plan issue from GitHub (must have 'erk-plan' label)
    2. Creates a worktree with auto-generated or custom name
    3. Saves issue reference for PR linking
    4. Changes to worktree directory and activates environment
    5. Automatically invokes Claude with /erk:implement-plan

    Args:
        issue_number: GitHub issue number with erk-plan label
        worktree_name: Optional custom worktree name (auto-generated if not provided)
        dry_run: Print actions without executing
        script: Output activation script for shell integration (hidden)
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Step 1: Fetch plan issue from GitHub
    try:
        plan_issue = ctx.plan_issue_store.get_plan_issue(repo_root, str(issue_number))
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Validate issue has erk-plan label
    if "erk-plan" not in plan_issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have the 'erk-plan' label.\n"
            + "Only issues tagged with 'erk-plan' can be used for implementation.\n\n"
            + f"To add the label, visit: {plan_issue.url}"
        )
        raise SystemExit(1)

    # Validate issue is open
    if plan_issue.state != PlanIssueState.OPEN:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Issue #{issue_number} is {plan_issue.state.value}. "
            + "Proceeding anyway..."
        )

    # Step 2: Determine worktree name
    if worktree_name:
        # User provided custom name - use as-is without date suffix
        name = sanitize_worktree_name(worktree_name)
    else:
        # Auto-generate from issue title with date suffix for uniqueness
        base_name = _generate_worktree_name_from_title(ctx, plan_issue.title)
        name = ensure_unique_worktree_name_with_date(base_name, repo.worktrees_dir, ctx.git)

    # Calculate worktree path
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    # Step 3: Handle dry-run mode
    if dry_run:
        dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
        user_output(dry_run_header + " No changes will be made\n")
        user_output(f"Would create worktree '{name}' from issue #{issue_number}")
        user_output(f"  Title: {plan_issue.title}")
        user_output(f'  Then run: {_build_claude_command("/erk:implement-plan", dangerous)}')
        return

    # Step 4: Create worktree from plan issue
    if not script:
        user_output(f"Creating worktree '{name}' for issue #{issue_number}...")

    # Create branch from trunk
    trunk_branch = ctx.trunk_branch
    branch = name  # Use worktree name as branch name

    # Check if branch already exists
    local_branches = ctx.git.list_local_branches(repo_root)
    if branch in local_branches:
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch '{branch}' already exists.\n"
            + "Cannot create worktree with existing branch name.\n"
            + "Use --worktree-name to specify a different name."
        )
        raise SystemExit(1)

    # Load local config for .env template and post-create commands
    config = (
        ctx.local_config
        if ctx.local_config is not None
        else LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    )

    # Respect global use_graphite config (matching erk create behavior)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create worktree
    add_worktree(
        ctx,
        repo_root,
        wt_path,
        branch=branch,
        ref=trunk_branch,
        use_existing_branch=False,
        use_graphite=use_graphite,
        skip_remote_check=True,
    )

    if not script:
        user_output(click.style(f"✓ Created worktree: {name}", fg="green"))

    # Run post-worktree setup (.env and post-create commands)
    run_post_worktree_setup(ctx, config, wt_path, repo_root, name)

    # Step 5: Create .impl/ folder with plan content
    create_impl_folder(
        worktree_path=wt_path,
        plan_content=plan_issue.body,
    )

    # Step 6: Save issue reference for PR linking
    issue_json = {"issue_number": issue_number, "issue_url": plan_issue.url}
    issue_json_path = wt_path / ".impl" / "issue.json"
    issue_json_path.write_text(json.dumps(issue_json, indent=2) + "\n", encoding="utf-8")

    if not script:
        user_output(click.style("✓ Saved issue reference for PR linking", fg="green"))

    # Step 7: Generate activation script (if --script flag)
    if script:
        # Render base activation script
        base_script = render_activation_script(
            worktree_path=wt_path,
            final_message='echo "Activated worktree: $(pwd)"',
            comment="plan-issue implement activation",
        )

        # Append Claude invocation command
        claude_command = f'{_build_claude_command("/erk:implement-plan", dangerous)}\n'
        full_script = base_script + claude_command

        # Write activation script using script writer
        result = ctx.script_writer.write_activation_script(
            full_script,
            command_name="plan-issue-implement",
            comment=f"activate {name} and run /erk:implement-plan",
        )

        # Output script path for shell integration
        result.output_for_shell_integration()
        return

    # Step 8: Provide fallback instructions (if no shell integration)
    user_output("\n" + click.style("Next steps:", fg="cyan", bold=True))
    user_output(f"  1. Change to worktree:  erk checkout {branch}")
    claude_cmd = _build_claude_command("/erk:implement-plan", dangerous)
    user_output(f"  2. Run implementation:  {claude_cmd}")
    user_output("\n" + click.style("Shell integration not detected.", fg="yellow"))
    user_output("To activate environment and run implementation, use:")
    user_output(f"  source <(erk plan-issue implement {issue_number} --script)")
