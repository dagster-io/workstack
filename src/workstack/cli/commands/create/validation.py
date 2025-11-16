"""Validation logic for the create command.

This module contains all validation functions used across the create command
implementation. All functions follow the LBYL (Look Before You Leap) pattern
and raise SystemExit on validation failure with clear error messages.
"""

from pathlib import Path

import click

from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.gitops import GitOps

from .types import CreateVariant, DotPlanSource


def identify_variant(
    from_current_branch: bool,
    from_branch: str | None,
    plan_file: Path | None,
    with_dot_plan_source: str | None,
) -> CreateVariant:
    """Determine which creation variant to use.

    Validates mutual exclusivity of flags and returns strongly-typed variant.

    Args:
        from_current_branch: --from-current-branch flag
        from_branch: --from-branch value
        plan_file: --plan file path
        with_dot_plan_source: --with-dot-plan source name

    Returns:
        CreateVariant literal indicating which variant to use

    Raises:
        SystemExit: If multiple mutually exclusive flags are provided
    """
    flags_set = sum(
        [
            from_current_branch,
            from_branch is not None,
            plan_file is not None,
            with_dot_plan_source is not None,
        ]
    )

    if flags_set > 1:
        user_output(
            "Cannot use multiple of: --from-current-branch, --from-branch, --plan, --with-dot-plan"
        )
        raise SystemExit(1)

    if from_current_branch:
        return "from_current_branch"
    elif from_branch is not None:
        return "from_branch"
    elif plan_file is not None:
        return "plan"
    elif with_dot_plan_source is not None:
        return "with_dot_plan"
    else:
        return "regular"


def validate_name(name: str) -> None:
    """Validate worktree name against reserved words.

    Args:
        name: Proposed worktree name

    Raises:
        SystemExit: If name is reserved ("root", "main", "master")
    """
    if name.lower() == "root":
        user_output('Error: "root" is a reserved name and cannot be used for a worktree.')
        raise SystemExit(1)

    if name.lower() in ("main", "master"):
        user_output(
            f'Error: "{name}" cannot be used as a worktree name.\n'
            f"To switch to the {name} branch in the root repository, use:\n"
            f"  workstack switch root",
        )
        raise SystemExit(1)


def validate_output_flags(output_json: bool, script: bool) -> None:
    """Validate output flags are not conflicting.

    Args:
        output_json: --json flag
        script: --script flag

    Raises:
        SystemExit: If both --json and --script are provided
    """
    if output_json and script:
        user_output("Error: Cannot use both --json and --script")
        raise SystemExit(1)


def validate_keep_plan_flag(keep_plan: bool, plan_file: Path | None) -> None:
    """Validate --keep-plan requires --plan.

    Args:
        keep_plan: --keep-plan flag
        plan_file: --plan file path

    Raises:
        SystemExit: If --keep-plan is used without --plan
    """
    if keep_plan and not plan_file:
        user_output("Error: --keep-plan requires --plan")
        raise SystemExit(1)


def validate_graphite_prerequisites(repo_root: Path, git_ops: GitOps) -> None:
    """Check Graphite can be used (no staged changes).

    Args:
        repo_root: Repository root path
        git_ops: Git operations interface

    Raises:
        SystemExit: If staged changes are detected
    """
    if git_ops.has_staged_changes(repo_root):
        user_output(click.style("Error: ", fg="red") + "Staged changes detected")
        user_output("Graphite requires a clean staging area.")
        user_output("Commit or unstage your changes:")
        user_output("  git commit -m 'Your message'")
        user_output("  # or")
        user_output("  git reset")
        raise SystemExit(1)


def validate_graphite_enabled(ctx: WorkstackContext) -> None:
    """Validate that Graphite is enabled in the configuration.

    Args:
        ctx: Workstack context

    Raises:
        SystemExit: If Graphite is not enabled
    """
    if not (ctx.global_config and ctx.global_config.use_graphite):
        user_output(
            click.style("Error: ", fg="red") + "--with-dot-plan requires Graphite to be enabled"
        )
        user_output("Enable Graphite in your workstack config: ~/.workstack/config.toml")
        user_output("  [graphite]")
        user_output("  enabled = true")
        raise SystemExit(1)


def resolve_source_workstack(
    ctx: WorkstackContext,
    workstacks_dir: Path,
    repo_root: Path,
    explicit_name: str | None,
) -> DotPlanSource:
    """Resolve and validate source workstack for --with-dot-plan.

    Handles both explicit (--with-dot-plan <name>) and implicit mode
    (--with-dot-plan without argument, uses current workstack).

    Args:
        ctx: Workstack context
        workstacks_dir: Path to workstacks directory
        repo_root: Repository root path
        explicit_name: Explicit source name or empty string for implicit

    Returns:
        DotPlanSource with validated source information

    Raises:
        SystemExit: If source invalid or .plan/ folder missing
    """
    # Resolve source workstack (explicit or implicit mode)
    if explicit_name:  # Non-empty string (explicit mode)
        source_name = explicit_name
    else:  # Empty string (implicit mode - flag used with no argument)
        # Detect current workstack from ctx.cwd
        if ctx.cwd.is_relative_to(workstacks_dir):
            try:
                relative = ctx.cwd.relative_to(workstacks_dir)
                source_name = relative.parts[0] if relative.parts else None
            except ValueError:
                source_name = None
        else:
            source_name = None

        if source_name is None:
            user_output(click.style("Error: ", fg="red") + "Cannot determine source workstack")
            user_output(
                "When using --with-dot-plan without an argument, you must be inside a workstack."
            )
            user_output("Either:")
            user_output("  • cd into a workstack directory first")
            user_output("  • Or specify the source: --with-dot-plan <workstack-name>")
            raise SystemExit(1)

    # Validate source workstack exists
    source_wt_path = workstacks_dir / source_name
    if not ctx.git_ops.path_exists(source_wt_path):
        user_output(
            click.style("Error: ", fg="red") + f"Source workstack '{source_name}' not found"
        )
        user_output(f"Available workstacks in {workstacks_dir}:")
        if ctx.git_ops.path_exists(workstacks_dir):
            worktrees = [d.name for d in workstacks_dir.iterdir() if d.is_dir()]
            if worktrees:
                for wt in sorted(worktrees):
                    user_output(f"  • {wt}")
            else:
                user_output("  (none)")
        raise SystemExit(1)

    # Verify source has .plan/ folder
    source_plan_path = source_wt_path / ".plan"
    if not ctx.git_ops.path_exists(source_plan_path):
        user_output(
            click.style("Error: ", fg="red")
            + f"Source workstack '{source_name}' has no .plan/ folder"
        )
        user_output("Create a workstack with a plan using:")
        user_output("  workstack create --plan <plan-file>")
        raise SystemExit(1)

    # Get source branch name
    source_branch = ctx.git_ops.get_current_branch(source_wt_path)
    if source_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Cannot determine branch for source workstack '{source_name}'"
        )
        raise SystemExit(1)

    # Get parent branch via Graphite
    parent_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo_root, source_branch)

    if parent_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Source branch '{source_branch}' has no parent in Graphite"
        )
        user_output("This could mean:")
        user_output(
            "  • Branch is not tracked by Graphite - run 'gt branch create' or 'gt stack fix'"
        )
        user_output("  • Branch is trunk (main/master) - cannot copy plan from trunk branch")
        raise SystemExit(1)

    return DotPlanSource(
        name=source_name,
        path=source_wt_path,
        branch=source_branch,
        parent_branch=parent_branch,
    )
