"""Orchestrator for the create command.

This is the main entry point for the create command. It handles CLI argument
parsing, validation, and dispatches to the appropriate variant handler.
The orchestrator is designed to be thin, delegating all complex logic to
specialized modules.
"""

from pathlib import Path

import click

from workstack.cli.commands.create.output import create_json_response, output_result
from workstack.cli.commands.create.post_creation import run_post_create_commands, write_env_file
from workstack.cli.commands.create.types import (
    CreateVariant,
    CreationRequest,
    CreationResult,
    OutputConfig,
    PlanConfig,
    WorktreeTarget,
)
from workstack.cli.commands.create.validation import (
    identify_variant,
    resolve_source_workstack,
    validate_graphite_enabled,
    validate_graphite_prerequisites,
    validate_keep_plan_flag,
    validate_name,
    validate_output_flags,
)
from workstack.cli.commands.create.variants.from_branch import create_from_branch
from workstack.cli.commands.create.variants.from_current_branch import create_from_current_branch
from workstack.cli.commands.create.variants.plan import create_with_plan
from workstack.cli.commands.create.variants.regular import create_regular
from workstack.cli.commands.create.variants.with_dot_plan import create_with_dot_plan
from workstack.cli.core import discover_repo_context, worktree_path_for
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.naming_utils import (
    ensure_unique_worktree_name,
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from workstack.core.plan_folder import get_plan_path
from workstack.core.repo_discovery import ensure_workstacks_dir


@click.command("create")
@click.argument("name", metavar="NAME", required=False)
@click.option(
    "--branch",
    "branch",
    type=str,
    help=("Branch name to create and check out in the worktree. Defaults to NAME if omitted."),
)
@click.option(
    "--ref",
    "ref",
    type=str,
    default=None,
    help=("Git ref to base the worktree on (e.g. HEAD, origin/main). Defaults to HEAD if omitted."),
)
@click.option(
    "--no-post",
    is_flag=True,
    help="Skip running post-create commands from config.toml.",
)
@click.option(
    "--plan",
    "plan_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "Path to a plan markdown file. Will derive worktree name from filename "
        "and create .plan/ folder with plan.md in the worktree. "
        "Worktree names are automatically suffixed with the current date (-YY-MM-DD) "
        "and versioned if duplicates exist."
    ),
)
@click.option(
    "--keep-plan",
    is_flag=True,
    help="Copy the plan file instead of moving it (requires --plan).",
)
@click.option(
    "--from-current-branch",
    is_flag=True,
    help=(
        "Move the current branch to the new worktree, then switch current worktree to --ref "
        "(defaults to main/master). NAME defaults to current branch name."
    ),
)
@click.option(
    "--from-branch",
    "from_branch",
    type=str,
    default=None,
    help=("Create worktree from an existing branch. NAME defaults to the branch name."),
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output JSON with worktree information instead of human-readable messages.",
)
@click.option(
    "--stay",
    is_flag=True,
    help="Stay in current directory instead of switching to new worktree.",
)
@click.option(
    "--with-dot-plan",
    "with_dot_plan_source",
    default=None,
    required=False,
    help=(
        "Copy .plan/ folder from source workstack. "
        "Optionally specify source workstack name. If not specified, uses current workstack."
    ),
)
@click.pass_obj
def create(
    ctx: WorkstackContext,
    name: str | None,
    branch: str | None,
    ref: str | None,
    no_post: bool,
    plan_file: Path | None,
    keep_plan: bool,
    from_current_branch: bool,
    from_branch: str | None,
    script: bool,
    output_json: bool,
    stay: bool,
    with_dot_plan_source: str | None,
) -> None:
    """Create a worktree and write a .env file.

    This command creates a new git worktree with various options for how
    the worktree and branch should be set up. It supports five distinct
    variants, each with its own specialized behavior.
    """
    # 1. Validate flags
    validate_output_flags(output_json, script)
    validate_keep_plan_flag(keep_plan, plan_file)

    # 2. Identify variant
    variant = identify_variant(from_current_branch, from_branch, plan_file, with_dot_plan_source)

    # 3. Build output config
    output_config = OutputConfig(
        mode="script" if script else ("json" if output_json else "human"),
        stay=stay,
    )

    # 4. Derive name based on variant
    derived_name = _derive_name(
        ctx, variant, name, branch, from_branch, plan_file, from_current_branch
    )

    # 5. Validate name
    validate_name(derived_name)

    # 6. Discover repo context
    repo = discover_repo_context(ctx, ctx.cwd)
    workstacks_dir = ensure_workstacks_dir(repo)

    # 7. Variant-specific validation and source resolution
    dot_plan_source = None
    if variant == "with_dot_plan":
        validate_graphite_enabled(ctx)
        validate_graphite_prerequisites(repo.root, ctx.git_ops)
        dot_plan_source = resolve_source_workstack(
            ctx, workstacks_dir, repo.root, with_dot_plan_source
        )

    # 8. Apply name transformations
    final_name = _apply_name_transformations(derived_name, variant, workstacks_dir)

    # 9. Build target configuration
    wt_path = worktree_path_for(workstacks_dir, final_name)

    # Check if worktree already exists
    if ctx.git_ops.path_exists(wt_path):
        _handle_existing_worktree(ctx, output_json, final_name, wt_path)

    target = WorktreeTarget(
        name=final_name,
        path=wt_path,
        repo_root=repo.root,
        workstacks_dir=workstacks_dir,
    )

    # 10. Build plan config if needed
    plan_config = None
    if plan_file:
        plan_config = PlanConfig(source_file=plan_file, keep_source=keep_plan)

    # 11. Prepare branch override for from_branch variant
    branch_override = branch
    if variant == "from_branch":
        # For from_branch, the branch name is the one being checked out
        branch_override = from_branch

    # 12. Build creation request
    request = CreationRequest(
        variant=variant,
        target=target,
        branch_override=branch_override,
        ref=ref,
        plan_config=plan_config,
        dot_plan_source=dot_plan_source,
        output=output_config,
        no_post=no_post,
    )

    # 13. Dispatch to variant
    result = _execute_variant(ctx, request)

    # 14. Post-creation operations
    write_env_file(target, ctx.local_config)

    if not no_post and ctx.local_config.post_create_commands:
        if not output_json:
            user_output("Running post-create commands...")
        run_post_create_commands(
            ctx.local_config.post_create_commands,
            target.path,
            ctx.local_config.post_create_shell,
        )

    # 15. Output results
    output_result(
        output_config,
        ctx,
        target,
        result.branch_config,
        variant,
        result.plan_dest,
        result.source_name,
    )


def _derive_name(
    ctx: WorkstackContext,
    variant: CreateVariant,
    name: str | None,
    branch: str | None,
    from_branch: str | None,
    plan_file: Path | None,
    from_current_branch: bool,
) -> str:
    """Derive the worktree name based on the variant and flags.

    Each variant has its own rules for deriving the name:
    - from_current_branch: Use current branch name if NAME not provided
    - from_branch: Use the branch name if NAME not provided
    - plan: Derive from plan filename (NAME forbidden)
    - with_dot_plan: NAME is required
    - regular: NAME is required

    Args:
        ctx: Workstack context
        variant: Which creation variant
        name: Explicit NAME argument
        branch: --branch flag value
        from_branch: --from-branch flag value
        plan_file: --plan file path
        from_current_branch: --from-current-branch flag

    Returns:
        Derived worktree name

    Raises:
        SystemExit: If required name is missing or conflicting flags
    """
    match variant:
        case "from_current_branch":
            current_branch_initial = ctx.git_ops.get_current_branch(ctx.cwd)
            if current_branch_initial is None:
                user_output("Error: HEAD is detached (not on a branch)")
                raise SystemExit(1)
            if branch:
                user_output(
                    "Cannot specify --branch with --from-current-branch (uses current branch)."
                )
                raise SystemExit(1)
            if not name:
                name = sanitize_worktree_name(current_branch_initial)

        case "from_branch":
            if branch:
                user_output(
                    "Cannot specify --branch with --from-branch (uses the specified branch)."
                )
                raise SystemExit(1)
            if not name:
                # from_branch is guaranteed to be non-None for this variant
                assert from_branch is not None, "from_branch must be set for from_branch variant"
                name = sanitize_worktree_name(from_branch)

        case "plan":
            if name:
                user_output("Cannot specify both NAME and --plan. Use one or the other.")
                raise SystemExit(1)
            # plan_file is guaranteed to be non-None for this variant
            assert plan_file is not None, "plan_file must be set for plan variant"
            plan_stem = plan_file.stem
            cleaned_stem = strip_plan_from_filename(plan_stem)
            name = sanitize_worktree_name(cleaned_stem)

        case "with_dot_plan":
            if not name:
                user_output("Must provide NAME with --with-dot-plan")
                raise SystemExit(1)

        case "regular":
            if not name:
                user_output(
                    "Must provide NAME or --plan or --from-branch or --from-current-branch option."
                )
                raise SystemExit(1)

    assert name is not None, "name must be set by now"
    return name


def _apply_name_transformations(
    name: str,
    variant: CreateVariant,
    workstacks_dir: Path,
) -> str:
    """Apply variant-specific name transformations.

    Args:
        name: Base name
        variant: Which creation variant
        workstacks_dir: Path to workstacks directory

    Returns:
        Final transformed name
    """
    # Sanitize name (for non-plan variants)
    is_plan_derived = variant == "plan"
    if not is_plan_derived:
        name = sanitize_worktree_name(name)

    # Apply unique naming for plan-derived names
    if is_plan_derived:
        name = ensure_unique_worktree_name(name, workstacks_dir)

    return name


def _handle_existing_worktree(
    ctx: WorkstackContext,
    output_json: bool,
    name: str,
    wt_path: Path,
) -> None:
    """Handle the case where a worktree already exists.

    Args:
        ctx: Workstack context
        output_json: Whether to output JSON
        name: Worktree name
        wt_path: Worktree path

    Raises:
        SystemExit: Always exits after handling
    """
    if output_json:
        existing_branch = ctx.git_ops.get_current_branch(wt_path)
        plan_path = get_plan_path(wt_path, git_ops=ctx.git_ops)
        json_response = create_json_response(
            worktree_name=name,
            worktree_path=wt_path,
            branch_name=existing_branch,
            plan_file_path=plan_path,
            status="exists",
        )
        user_output(json_response)
        raise SystemExit(1)
    else:
        user_output(f"Worktree path already exists: {wt_path}")
        raise SystemExit(1)


def _execute_variant(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Dispatch to variant-specific creation logic.

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult from the variant handler

    Raises:
        ValueError: If unknown variant (should never happen)
    """
    match request.variant:
        case "regular":
            return create_regular(ctx, request)
        case "from_current_branch":
            return create_from_current_branch(ctx, request)
        case "from_branch":
            return create_from_branch(ctx, request)
        case "plan":
            return create_with_plan(ctx, request)
        case "with_dot_plan":
            return create_with_dot_plan(ctx, request)
        case _:
            raise ValueError(f"Unknown variant: {request.variant}")
