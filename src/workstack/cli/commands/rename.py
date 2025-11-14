import click

from workstack.cli.commands.create import make_env_content, sanitize_worktree_name
from workstack.cli.commands.switch import complete_worktree_names
from workstack.cli.core import discover_repo_context, worktree_path_for
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext, create_context
from workstack.core.repo_discovery import ensure_workstacks_dir


@click.command("rename")
@click.argument("old_name", metavar="OLD_NAME", shell_complete=complete_worktree_names)
@click.argument("new_name", metavar="NEW_NAME")
@click.option(
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def rename_cmd(ctx: WorkstackContext, old_name: str, new_name: str, dry_run: bool) -> None:
    """Rename a worktree directory.

    Renames the worktree directory and updates git metadata.
    The .env file is regenerated with updated paths and name.
    """
    # Create dry-run context if needed
    if dry_run:
        ctx = create_context(dry_run=True)

    # Sanitize new name
    sanitized_new_name = sanitize_worktree_name(new_name)

    repo = discover_repo_context(ctx, ctx.cwd)
    workstacks_dir = ensure_workstacks_dir(repo)

    old_path = worktree_path_for(workstacks_dir, old_name)
    new_path = worktree_path_for(workstacks_dir, sanitized_new_name)

    # Validate old worktree exists
    if not ctx.git_ops.path_exists(old_path):
        user_output(f"Worktree not found: {old_path}")
        raise SystemExit(1)

    # Validate new path doesn't already exist
    if ctx.git_ops.path_exists(new_path):
        user_output(f"Destination already exists: {new_path}")
        raise SystemExit(1)

    # Move via git worktree move
    ctx.git_ops.move_worktree(repo.root, old_path, new_path)

    # Regenerate .env file with updated paths and name
    cfg = ctx.local_config
    env_content = make_env_content(
        cfg, worktree_path=new_path, repo_root=repo.root, name=sanitized_new_name
    )

    # Write .env file (dry-run vs real)
    env_file = new_path / ".env"
    if ctx.dry_run:
        user_output(f"[DRY RUN] Would write .env file: {env_file}")
    else:
        env_file.write_text(env_content, encoding="utf-8")

    user_output(f"Renamed worktree: {old_name} -> {sanitized_new_name}")
    user_output(str(new_path))
