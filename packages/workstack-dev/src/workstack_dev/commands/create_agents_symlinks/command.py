"""Create CLAUDE.md reference files command.

Following the AGENTS.md standard where AGENTS.md is the primary file
and CLAUDE.md is a reference file containing @AGENTS.md for backwards compatibility.

See: https://code.claude.com/docs/en/claude-code-on-the-web
"""

from pathlib import Path

import click


def is_git_repo_root(path: Path) -> bool:
    """Return True when the path looks like a git repository root."""
    git_dir = path / ".git"
    return git_dir.exists() and git_dir.is_dir()


def create_reference_for_agents_md(agents_md_path: Path, dry_run: bool) -> str:
    """Create CLAUDE.md reference file for the provided AGENTS.md file."""
    claude_md_path = agents_md_path.parent / "CLAUDE.md"

    if claude_md_path.exists():
        if claude_md_path.is_file() and not claude_md_path.is_symlink():
            # Check if it already contains @AGENTS.md
            content = claude_md_path.read_text(encoding="utf-8")
            if content.strip() == "@AGENTS.md":
                return "skipped_correct"
        return "skipped_exists"

    if not dry_run:
        claude_md_path.write_text("@AGENTS.md", encoding="utf-8")

    return "created"


def create_agents_symlinks(repo_root: Path, dry_run: bool, verbose: bool) -> tuple[int, int]:
    """Create missing CLAUDE.md reference files underneath the repository root."""
    created_count = 0
    skipped_count = 0

    agents_md_files = list(repo_root.rglob("AGENTS.md"))

    if verbose:
        plural = "s" if len(agents_md_files) != 1 else ""
        click.echo(f"Found {len(agents_md_files)} AGENTS.md file{plural}")

    for agents_md_path in agents_md_files:
        status = create_reference_for_agents_md(agents_md_path, dry_run)

        rel_path = agents_md_path.relative_to(repo_root)
        if status == "created":
            created_count += 1
            if verbose:
                action = "Would create" if dry_run else "Created"
                click.echo(f"  ✓ {action}: {rel_path.parent}/CLAUDE.md")
        else:
            skipped_count += 1
            if verbose:
                click.echo(f"  ⊘ Skipped: {rel_path.parent}/CLAUDE.md (already exists)")

    return created_count, skipped_count


@click.command(name="create-agents-symlinks")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def create_agents_symlinks_command(dry_run: bool, verbose: bool) -> None:
    """Create CLAUDE.md reference files for all AGENTS.md files in the repository.

    Following the AGENTS.md standard, this command creates CLAUDE.md files
    containing '@AGENTS.md' for backwards compatibility with existing tools
    that expect CLAUDE.md.
    """
    repo_root = Path.cwd()
    if not is_git_repo_root(repo_root):
        click.echo("Error: Must be run from git repository root", err=True)
        raise SystemExit(1)

    created_count, skipped_count = create_agents_symlinks(repo_root, dry_run, verbose)

    if not verbose and (created_count > 0 or skipped_count > 0):
        if dry_run:
            if created_count > 0:
                plural = "s" if created_count != 1 else ""
                click.echo(f"Would create {created_count} CLAUDE.md reference{plural}")
            if skipped_count > 0:
                click.echo(f"Would skip {skipped_count} (already exists)")
        else:
            if created_count > 0:
                plural = "s" if created_count != 1 else ""
                click.echo(f"✓ Created {created_count} CLAUDE.md reference{plural}")
            if skipped_count > 0:
                click.echo(f"⊘ Skipped {skipped_count} (already exists)")
    elif created_count == 0 and skipped_count == 0:
        click.echo("No AGENTS.md files found")
