"""Admin commands for repository configuration."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.implementation_queue.github import RealGitHubAdmin


@click.group("admin")
def admin_group() -> None:
    """Administrative commands for repository configuration."""
    pass


@admin_group.command("github-pr-setting")
@click.option(
    "--enable",
    "action",
    flag_value="enable",
    help="Enable PR creation for GitHub Actions workflows",
)
@click.option(
    "--disable",
    "action",
    flag_value="disable",
    help="Disable PR creation for GitHub Actions workflows",
)
@click.pass_obj
def github_pr_setting(ctx: ErkContext, action: str | None) -> None:
    """Manage GitHub Actions workflow permission for PR creation.

    Without flags: Display current setting
    With --enable: Enable PR creation for workflows
    With --disable: Disable PR creation for workflows

    This setting controls whether GitHub Actions workflows can create
    and approve pull requests in your repository.

    GitHub UI location: Settings > Actions > General > Workflow permissions
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Create admin interface
    # TODO: Use injected admin from context when dry-run support is added
    admin = RealGitHubAdmin()

    if action is None:
        # Display current setting
        try:
            perms = admin.get_workflow_permissions(repo.root)
            enabled = perms.get("can_approve_pull_request_reviews", False)

            user_output(click.style("GitHub Actions PR Creation Setting", bold=True))
            user_output("")

            status_text = "Enabled" if enabled else "Disabled"
            status_color = "green" if enabled else "red"
            user_output(f"Current status: {click.style(status_text, fg=status_color)}")
            user_output("")

            if enabled:
                user_output("Workflows can create and approve pull requests in this repository.")
            else:
                user_output("Workflows cannot create pull requests in this repository.")

            user_output("")
            user_output(click.style("GitHub UI location:", fg="white", dim=True))
            user_output(
                click.style(
                    "  Settings > Actions > General > Workflow permissions",
                    fg="white",
                    dim=True,
                )
            )

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e

    elif action == "enable":
        # Enable PR creation
        try:
            admin.set_workflow_pr_permissions(repo.root, enabled=True)

            user_output(
                click.style("✓", fg="green") + " Enabled PR creation for GitHub Actions workflows"
            )
            user_output("")
            user_output("Workflows can now create and approve pull requests.")

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e

    elif action == "disable":
        # Disable PR creation
        try:
            admin.set_workflow_pr_permissions(repo.root, enabled=False)

            user_output(
                click.style("✓", fg="green") + " Disabled PR creation for GitHub Actions workflows"
            )
            user_output("")
            user_output("Workflows can no longer create pull requests.")

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e
