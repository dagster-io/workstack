"""Command to implement features from GitHub issues or plan files.

This unified command provides two modes:
- GitHub issue mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md

Both modes create a worktree and invoke Claude for implementation.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import click

from dot_agent_kit.data.kits.erk.plan_utils import generate_filename_from_title
from erk.cli.activation import render_activation_script
from erk.cli.commands.create import add_worktree, run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.impl_folder import create_impl_folder
from erk.core.naming_utils import (
    ensure_unique_worktree_name_with_date,
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from erk.core.plan_issue_store.types import PlanIssueState
from erk.core.repo_discovery import ensure_erk_metadata_dir


class TargetInfo(NamedTuple):
    """Information about detected target type.

    Attributes:
        target_type: Type of target - "issue_number", "issue_url", or "file_path"
        issue_number: Extracted issue number for GitHub targets, None for file paths
    """

    target_type: str
    issue_number: str | None


@dataclass(frozen=True)
class PlanSource:
    """Source information for creating a worktree with plan.

    Attributes:
        plan_content: The plan content as a string
        base_name: Base name for generating worktree name
        dry_run_description: Description to show in dry-run mode
    """

    plan_content: str
    base_name: str
    dry_run_description: str


def _detect_target_type(target: str) -> TargetInfo:
    """Detect whether target is an issue number, issue URL, or file path.

    Args:
        target: User-provided target argument

    Returns:
        TargetInfo with target type and extracted issue number (if applicable)
    """
    # Check if starts with # followed by digits (issue number)
    if target.startswith("#") and target[1:].isdigit():
        return TargetInfo(target_type="issue_number", issue_number=target[1:])

    # Check if GitHub issue URL
    github_issue_pattern = r"github\.com/[^/]+/[^/]+/issues/(\d+)"
    match = re.search(github_issue_pattern, target)
    if match:
        issue_number = match.group(1)
        return TargetInfo(target_type="issue_url", issue_number=issue_number)

    # Otherwise, treat as file path
    return TargetInfo(target_type="file_path", issue_number=None)


def _prepare_plan_source_from_issue(
    ctx: ErkContext, repo_root: Path, issue_number: str
) -> PlanSource:
    """Prepare plan source from GitHub issue.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        issue_number: GitHub issue number

    Returns:
        PlanSource with plan content and metadata

    Raises:
        SystemExit: If issue not found or doesn't have erk-plan label
    """
    # Fetch plan issue from GitHub
    try:
        plan_issue = ctx.plan_issue_store.get_plan_issue(repo_root, issue_number)
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

    # Generate base name from issue title
    filename = generate_filename_from_title(plan_issue.title)
    stem = filename.removesuffix(".md")
    base_name = strip_plan_from_filename(stem)

    dry_run_desc = f"Would create worktree from issue #{issue_number}\n  Title: {plan_issue.title}"

    return PlanSource(
        plan_content=plan_issue.body,
        base_name=base_name,
        dry_run_description=dry_run_desc,
    )


def _prepare_plan_source_from_file(plan_file: Path) -> PlanSource:
    """Prepare plan source from file.

    Args:
        plan_file: Path to plan file

    Returns:
        PlanSource with plan content and metadata

    Raises:
        SystemExit: If plan file doesn't exist
    """
    # Validate plan file exists
    if not plan_file.exists():
        user_output(click.style("Error: ", fg="red") + f"Plan file not found: {plan_file}")
        raise SystemExit(1)

    # Read plan content
    plan_content = plan_file.read_text(encoding="utf-8")

    # Derive base name from filename
    plan_stem = plan_file.stem
    cleaned_stem = strip_plan_from_filename(plan_stem)
    base_name = sanitize_worktree_name(cleaned_stem)

    dry_run_desc = (
        f"Would create worktree from plan file: {plan_file}\n"
        f"  Plan file would be deleted: {plan_file}"
    )

    return PlanSource(
        plan_content=plan_content,
        base_name=base_name,
        dry_run_description=dry_run_desc,
    )


def _save_issue_reference(wt_path: Path, issue_number: str, issue_url: str) -> None:
    """Save issue reference to .impl/issue.json for PR linking.

    Args:
        wt_path: Worktree path
        issue_number: GitHub issue number
        issue_url: GitHub issue URL
    """
    issue_json = {"issue_number": int(issue_number), "issue_url": issue_url}
    issue_json_path = wt_path / ".impl" / "issue.json"
    issue_json_path.write_text(json.dumps(issue_json, indent=2) + "\n", encoding="utf-8")


def _create_worktree_with_plan_content(
    ctx: ErkContext,
    plan_source: PlanSource,
    worktree_name: str | None,
    dry_run: bool,
    script: bool,
) -> Path | None:
    """Create worktree with plan content.

    Args:
        ctx: Erk context
        plan_source: Plan source with content and metadata
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        script: Whether to output activation script

    Returns:
        Path to created worktree, or None if dry-run mode
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Determine worktree name
    if worktree_name:
        name = sanitize_worktree_name(worktree_name)
    else:
        name = ensure_unique_worktree_name_with_date(
            plan_source.base_name, repo.worktrees_dir, ctx.git
        )

    # Calculate worktree path
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    # Handle dry-run mode
    if dry_run:
        dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
        user_output(dry_run_header + " No changes will be made\n")
        user_output(f"Would create worktree '{name}'")
        user_output(f"  {plan_source.dry_run_description}")
        user_output('  Then run: claude --permission-mode acceptEdits "/erk:implement-plan"')
        return None

    # Create worktree
    if not script:
        user_output(f"Creating worktree '{name}'...")

    trunk_branch = ctx.trunk_branch
    branch = name

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

    # Load local config
    config = (
        ctx.local_config
        if ctx.local_config is not None
        else LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    )

    # Create worktree
    add_worktree(
        ctx,
        repo_root,
        wt_path,
        branch=branch,
        ref=trunk_branch,
        use_existing_branch=False,
        use_graphite=False,
        skip_remote_check=True,
    )

    if not script:
        user_output(click.style(f"✓ Created worktree: {name}", fg="green"))

    # Run post-worktree setup
    run_post_worktree_setup(config, wt_path, repo_root, name)

    # Create .impl/ folder with plan content
    create_impl_folder(
        worktree_path=wt_path,
        plan_content=plan_source.plan_content,
    )

    return wt_path


def _output_activation_instructions(
    ctx: ErkContext,
    wt_path: Path,
    branch: str,
    script: bool,
    target_description: str,
) -> None:
    """Output activation script or manual instructions.

    Args:
        ctx: Erk context
        wt_path: Worktree path
        branch: Branch name
        script: Whether to output activation script
        target_description: Description of target for user messages
    """
    if script:
        # Generate activation script
        base_script = render_activation_script(
            worktree_path=wt_path,
            final_message='echo "Activated worktree: $(pwd)"',
            comment="implement activation",
        )

        claude_command = 'claude --permission-mode acceptEdits "/erk:implement-plan"\n'
        full_script = base_script + claude_command

        result = ctx.script_writer.write_activation_script(
            full_script,
            command_name="implement",
            comment=f"activate {wt_path.name} and run /erk:implement-plan",
        )

        result.output_for_shell_integration()
    else:
        # Provide manual instructions
        user_output("\n" + click.style("Next steps:", fg="cyan", bold=True))
        user_output(f"  1. Change to worktree:  erk checkout {branch}")
        claude_cmd = 'claude --permission-mode acceptEdits "/erk:implement-plan"'
        user_output(f"  2. Run implementation:  {claude_cmd}")
        user_output("\n" + click.style("Shell integration not detected.", fg="yellow"))
        user_output("To activate environment and run implementation, use:")
        user_output(f"  source <(erk implement {target_description} --script)")


def _implement_from_issue(
    ctx: ErkContext,
    issue_number: str,
    worktree_name: str | None,
    dry_run: bool,
    script: bool,
) -> None:
    """Implement feature from GitHub issue.

    Args:
        ctx: Erk context
        issue_number: GitHub issue number
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        script: Whether to output activation script
    """
    # Discover repo context for issue fetch
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Prepare plan source from issue
    plan_source = _prepare_plan_source_from_issue(ctx, repo.root, issue_number)

    # Create worktree with plan content
    wt_path = _create_worktree_with_plan_content(ctx, plan_source, worktree_name, dry_run, script)

    # Early return for dry-run mode
    if wt_path is None:
        return

    # Save issue reference for PR linking (issue-specific)
    plan_issue = ctx.plan_issue_store.get_plan_issue(repo.root, issue_number)
    _save_issue_reference(wt_path, issue_number, plan_issue.url)

    if not script:
        user_output(click.style("✓ Saved issue reference for PR linking", fg="green"))

    # Output activation instructions
    branch = wt_path.name
    target_description = f"#{issue_number}"
    _output_activation_instructions(ctx, wt_path, branch, script, target_description)


def _implement_from_file(
    ctx: ErkContext,
    plan_file: Path,
    worktree_name: str | None,
    dry_run: bool,
    script: bool,
) -> None:
    """Implement feature from plan file.

    Args:
        ctx: Erk context
        plan_file: Path to plan file
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        script: Whether to output activation script
    """
    # Prepare plan source from file
    plan_source = _prepare_plan_source_from_file(plan_file)

    # Create worktree with plan content
    wt_path = _create_worktree_with_plan_content(ctx, plan_source, worktree_name, dry_run, script)

    # Early return for dry-run mode
    if wt_path is None:
        return

    # Delete original plan file (move semantics, file-specific)
    plan_file.unlink()

    if not script:
        user_output(click.style("✓ Moved plan file to worktree", fg="green"))

    # Output activation instructions
    branch = wt_path.name
    target_description = str(plan_file)
    _output_activation_instructions(ctx, wt_path, branch, script, target_description)


@click.command("implement")
@click.argument("target")
@click.option(
    "--worktree-name",
    type=str,
    default=None,
    help="Override worktree name (optional, auto-generated if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be executed without doing it",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output activation script for shell integration",
)
@click.pass_obj
def implement(
    ctx: ErkContext,
    target: str,
    worktree_name: str | None,
    dry_run: bool,
    script: bool,
) -> None:
    """Create worktree from GitHub issue or plan file and invoke Claude.

    TARGET can be:
    - GitHub issue number with # prefix (e.g., #123)
    - GitHub issue URL (e.g., https://github.com/user/repo/issues/123)
    - Path to plan file (e.g., ./my-feature-plan.md or 123)

    For GitHub issues, the issue must have the 'erk-plan' label.

    Examples:

    \b
      # From GitHub issue number (requires # prefix)
      erk implement #123

    \b
      # From GitHub issue URL
      erk implement https://github.com/user/repo/issues/123

    \b
      # From plan file
      erk implement ./my-feature-plan.md

    \b
      # File named "123" (no # prefix means file path)
      erk implement 123

    \b
      # With custom worktree name
      erk implement #123 --worktree-name my-custom-name

    \b
      # Dry run to see what would happen
      erk implement #123 --dry-run
    """
    # Detect target type
    target_info = _detect_target_type(target)

    if target_info.target_type in ("issue_number", "issue_url"):
        # GitHub issue mode
        if target_info.issue_number is None:
            user_output(
                click.style("Error: ", fg="red") + "Failed to extract issue number from target"
            )
            raise SystemExit(1)

        _implement_from_issue(ctx, target_info.issue_number, worktree_name, dry_run, script)
    else:
        # Plan file mode
        plan_file = Path(target)
        _implement_from_file(ctx, plan_file, worktree_name, dry_run, script)
