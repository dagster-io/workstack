#!/usr/bin/env python3
"""Get PR metadata section for PR body.

This command builds a metadata section for PR bodies containing:
- Plan link (if .impl/issue.json exists)
- Plan author (if .impl/plan.md has created_by in plan-header)
- Checkout command (with PR number or placeholder)
- Closes reference (if issue exists)
- Horizontal rule separator

Usage:
    # Get metadata section without PR number (uses placeholder)
    pr_metadata=$(dot-agent run erk get-pr-metadata 2>/dev/null || echo "")

    # Get metadata section with actual PR number
    pr_metadata=$(dot-agent run erk get-pr-metadata --pr-number 123 2>/dev/null || echo "")

Output:
    - If metadata exists: Formatted metadata section
    - If no metadata: empty string (no output)

Exit Codes:
    0: Success (always succeeds, even if no metadata)

Examples:
    $ cd worktree-with-issue
    $ dot-agent run erk get-pr-metadata
    - **Plan:** [#123](https://github.com/owner/repo/issues/123)
    - **Plan Author:** @username
    ...

    $ cd worktree-without-issue
    $ dot-agent run erk get-pr-metadata
    (no output)
"""

from pathlib import Path

import click


@click.command(name="get-pr-metadata")
@click.option(
    "--pr-number",
    type=int,
    default=None,
    help="PR number for checkout command (uses placeholder if not provided)",
)
def get_pr_metadata(pr_number: int | None) -> None:
    """Get PR metadata section for PR body.

    Builds metadata section from .impl/ directory contents:
    - Issue reference from .impl/issue.json
    - Plan author from .impl/plan.md metadata
    - Checkout command with PR number or placeholder

    This command is designed for use in PR creation workflows where metadata
    is optional functionality that should degrade gracefully.
    """
    from erk_shared.impl_folder import (
        has_issue_reference,
        read_issue_reference,
        read_plan_author,
    )

    impl_dir = Path.cwd() / ".impl"

    # Read all available metadata
    issue_ref = read_issue_reference(impl_dir) if has_issue_reference(impl_dir) else None
    plan_author = read_plan_author(impl_dir)

    # Only build metadata if we have something to show
    if issue_ref is None and plan_author is None:
        return

    metadata_parts: list[str] = []

    # Build bullets
    bullets: list[str] = []
    if issue_ref is not None:
        bullets.append(f"- **Plan:** [#{issue_ref.issue_number}]({issue_ref.issue_url})")
    if plan_author is not None:
        bullets.append(f"- **Plan Author:** @{plan_author}")

    if bullets:
        metadata_parts.append("\n".join(bullets) + "\n")

    # Checkout command (with placeholder or actual number)
    pr_display = str(pr_number) if pr_number is not None else "__PLACEHOLDER_PR_NUMBER__"
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_display}\n"
        f"```\n"
    )

    # Closes #N
    if issue_ref is not None:
        metadata_parts.append(f"\nCloses #{issue_ref.issue_number}\n")

    # Separator
    metadata_parts.append("\n---\n")

    # Output metadata section
    output = "\n".join(metadata_parts)
    click.echo(output, nl=False)
