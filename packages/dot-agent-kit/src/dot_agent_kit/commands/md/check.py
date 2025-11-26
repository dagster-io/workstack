"""Check AGENTS.md standard compliance command.

This command validates that repositories follow the AGENTS.md standard where:
- AGENTS.md is the primary context file
- CLAUDE.md contains '@AGENTS.md' reference for backwards compatibility
- (Optional) All @ file references point to existing files with valid fragments

See: https://code.claude.com/docs/en/claude-code-on-the-web
"""

import subprocess
from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io.link_validation import BrokenLink, validate_links_in_file


def _discover_markdown_files(repo_root: Path) -> list[Path]:
    """Discover all markdown files to check for @ references.

    Discovers:
    - All CLAUDE.md files in the repository
    - All .md files in .claude/ directories
    - All .md files in .agent/ directories

    Args:
        repo_root: Repository root path

    Returns:
        List of unique markdown file paths to check
    """
    files: set[Path] = set()

    # All CLAUDE.md files
    for claude_file in repo_root.rglob("CLAUDE.md"):
        files.add(claude_file)

    # All .md files in .claude/ directories
    for claude_dir in repo_root.rglob(".claude"):
        if claude_dir.is_dir():
            for md_file in claude_dir.rglob("*.md"):
                files.add(md_file)

    # All .md files in .agent/ directories
    for agent_dir in repo_root.rglob(".agent"):
        if agent_dir.is_dir():
            for md_file in agent_dir.rglob("*.md"):
                files.add(md_file)

    return sorted(files)


@click.command(name="check")
@click.option(
    "--check-links",
    is_flag=True,
    default=False,
    help="Also validate that @ file references point to existing files.",
)
def check_command(*, check_links: bool) -> None:
    """Validate AGENTS.md standard compliance in the repository.

    Checks that:
    - Every CLAUDE.md file has a peer AGENTS.md file
    - Every CLAUDE.md file contains '@AGENTS.md' reference

    With --check-links:
    - All @ file references point to existing files
    - All # fragment anchors reference valid headings

    Exit codes:
    - 0: All checks passed
    - 1: Violations found
    """
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    repo_root_str = result.stdout.strip()
    repo_root_path = Path(repo_root_str)

    if not repo_root_path.exists():
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    # Find all CLAUDE.md files
    claude_files = list(repo_root_path.rglob("CLAUDE.md"))

    if len(claude_files) == 0:
        user_output(click.style("ℹ️  No CLAUDE.md files found in repository", fg="cyan"))
        raise SystemExit(0)

    # Track violations
    missing_agents: list[Path] = []
    invalid_content: list[Path] = []
    broken_links: list[BrokenLink] = []

    for claude_path in claude_files:
        # Check for peer AGENTS.md
        agents_path = claude_path.parent / "AGENTS.md"
        if not agents_path.exists():
            missing_agents.append(claude_path.parent)
            continue

        # Check CLAUDE.md content
        content = claude_path.read_text(encoding="utf-8")
        if content.strip() != "@AGENTS.md":
            invalid_content.append(claude_path)

    # Optionally validate @ references
    all_md_files: list[Path] = []
    if check_links:
        all_md_files = _discover_markdown_files(repo_root_path)
        for md_file in all_md_files:
            broken_links.extend(validate_links_in_file(md_file, repo_root_path))

    # Report results
    violation_count = len(missing_agents) + len(invalid_content) + len(broken_links)
    if violation_count == 0:
        user_output(click.style("✓ AGENTS.md standard: PASSED", fg="green", bold=True))
        user_output()
        user_output("All CLAUDE.md files properly reference AGENTS.md.")
        if check_links:
            user_output("All @ references are valid.")
        user_output()
        user_output(f"CLAUDE.md files checked: {len(claude_files)}")
        if check_links:
            user_output(f"Markdown files checked for @ references: {len(all_md_files)}")
        user_output("Violations: 0")
        raise SystemExit(0)

    # Found violations
    user_output(click.style("✗ AGENTS.md standard: FAILED", fg="red", bold=True))
    user_output()
    plural = "s" if violation_count != 1 else ""
    user_output(f"Found {violation_count} violation{plural}:")
    user_output()

    if len(missing_agents) > 0:
        user_output(click.style("Missing AGENTS.md:", fg="yellow"))
        for path in missing_agents:
            rel_path = path.relative_to(repo_root_path)
            user_output(f"  • {click.style(str(rel_path) + '/', fg='cyan')}")
        user_output()

    if len(invalid_content) > 0:
        user_output(click.style("Invalid CLAUDE.md content:", fg="yellow"))
        for path in invalid_content:
            rel_path = path.relative_to(repo_root_path)
            content = path.read_text(encoding="utf-8")
            styled_path = click.style(str(rel_path), fg="cyan")
            user_output(f"  • {styled_path}: Content is '{content.strip()}', expected '@AGENTS.md'")
        user_output()

    if len(broken_links) > 0:
        user_output(click.style("Broken @ references:", fg="yellow"))
        for broken in broken_links:
            source_rel = broken.source_file.relative_to(repo_root_path)
            styled_source = click.style(f"{source_rel}:{broken.reference.line_number}", fg="cyan")
            if broken.error_type == "missing_file":
                user_output(f"  • {styled_source}: File not found: {broken.reference.raw_text}")
            elif broken.error_type == "missing_fragment":
                user_output(f"  • {styled_source}: Fragment not found: #{broken.error_detail}")
        user_output()

    user_output("Fix these issues and run again.")
    raise SystemExit(1)
