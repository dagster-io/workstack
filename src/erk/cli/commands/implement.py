"""CLI command for executing implementation plans.

Provides `erk implement` command with optional `--docker` flag to execute
implementation plans either natively on host or inside Docker containers.
"""

from pathlib import Path

import click

from erk.cli.output import user_output
from erk.core.docker_implement import execute_docker_implementation
from erk.core.native_implement import execute_native_implementation
from erk.core.shell import RealShell
from erk.ops.docker_real import RealDocker


@click.command("implement")
@click.option(
    "--docker",
    is_flag=True,
    default=False,
    help="Execute in Docker container (requires .erk/sandboxes/default/Dockerfile)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without executing",
)
@click.pass_context
def implement(ctx: click.Context, docker: bool, dry_run: bool) -> None:
    """Execute implementation plan from current worktree.

    Runs `/erk:implement-plan` command either natively on host or inside
    Docker container. Requires `.plan/plan.md` in current directory.

    Examples:
        erk implement              # Native execution on host
        erk implement --docker     # Docker execution in container
        erk implement --dry-run    # Show what would happen

    The --docker flag requires:
        - .erk/sandboxes/default/Dockerfile in current worktree
        - Docker daemon running
        - Docker CLI installed
    """
    # Get current working directory as worktree root
    cwd = Path.cwd()

    # LBYL: Check plan exists before any setup
    plan_file = cwd / ".plan" / "plan.md"
    if not plan_file.exists():
        user_output(
            click.style("❌ Error: ", fg="red")
            + "No plan found in current directory\n\n"
            + "Expected: "
            + click.style(str(plan_file), fg="white", dim=True)
            + "\n\n"
            + "To create a plan, run one of:\n"
            + "  • "
            + click.style("/erk:persist-plan", fg="cyan")
            + " - Save plan from conversation\n"
            + "  • "
            + click.style("/erk:create-planned-wt", fg="cyan")
            + " - Create worktree from plan file"
        )
        raise SystemExit(1)

    # Handle dry-run mode
    if dry_run:
        user_output(click.style("🔍 Dry run mode - showing what would be done\n", bold=True))
        user_output(
            f"Worktree: {click.style(str(cwd), fg='yellow')}\n"
            + f"Plan file: {click.style(str(plan_file), fg='green')}\n"
        )
        if docker:
            dockerfile = cwd / ".erk" / "sandboxes" / "default" / "Dockerfile"
            user_output(
                f"Mode: {click.style('Docker', fg='cyan', bold=True)}\n"
                + f"Dockerfile: {click.style(str(dockerfile), fg='yellow')}\n"
            )
            user_output("\nWould execute:\n")
            user_output(
                "  1. Build Docker image from sandbox Dockerfile\n"
                + "  2. Mount worktree at /workspace\n"
                + "  3. Mount git config and SSH keys (read-only)\n"
                + "  4. Run: claude --permission-mode acceptEdits /erk:implement-plan\n"
                + "  5. Destroy container on completion\n"
            )
        else:
            user_output(f"Mode: {click.style('Native', fg='green', bold=True)}\n")
            user_output("\nWould execute:\n")
            user_output("  • Run: claude --permission-mode acceptEdits /erk:implement-plan\n")
        return

    # Docker mode
    if docker:
        # LBYL: Check Dockerfile exists before any Docker operations
        dockerfile = cwd / ".erk" / "sandboxes" / "default" / "Dockerfile"
        if not dockerfile.exists():
            user_output(
                click.style("❌ Error: ", fg="red")
                + "Sandbox Dockerfile not found\n\n"
                + "Expected: "
                + click.style(str(dockerfile), fg="white", dim=True)
                + "\n\n"
                + "To create a sandbox:\n"
                + "  1. Create directory: "
                + click.style("mkdir -p .erk/sandboxes/default", fg="cyan")
                + "\n"
                + "  2. Copy template from: "
                + click.style("docs/examples/sandboxes/python-example/", fg="cyan")
                + "\n"
                + "  3. Customize Dockerfile for your project needs"
            )
            raise SystemExit(1) from None

        # Display status
        user_output(
            "\n"
            + click.style("🐳 Docker Implementation Mode\n", bold=True)
            + f"Worktree: {click.style(str(cwd), fg='yellow')}\n"
            + f"Sandbox: {click.style('default', fg='cyan', bold=True)}\n"
        )

        # Execute in Docker
        try:
            docker_ops = RealDocker()
            exit_code = execute_docker_implementation(
                docker=docker_ops,
                worktree_root=cwd,
                sandbox_name="default",
            )

            if exit_code == 0:
                user_output("\n" + click.style("✅ Implementation complete", fg="green") + "\n")
            else:
                user_output(
                    "\n"
                    + click.style(f"❌ Implementation failed with exit code {exit_code}", fg="red")
                    + "\n"
                )

            raise SystemExit(exit_code)

        except FileNotFoundError as e:
            user_output(click.style("❌ Error: ", fg="red") + str(e))
            raise SystemExit(1) from None
        except RuntimeError as e:
            user_output(click.style("❌ Error: ", fg="red") + str(e))
            raise SystemExit(1) from None

    # Native mode
    else:
        # Display status
        user_output(
            "\n"
            + click.style("💻 Native Implementation Mode\n", bold=True)
            + f"Worktree: {click.style(str(cwd), fg='yellow')}\n"
        )

        # Execute natively
        try:
            shell_ops = RealShell()
            exit_code = execute_native_implementation(shell_ops, cwd)

            if exit_code == 0:
                user_output("\n" + click.style("✅ Implementation complete", fg="green") + "\n")
            else:
                user_output(
                    "\n"
                    + click.style(f"❌ Implementation failed with exit code {exit_code}", fg="red")
                    + "\n"
                )

            raise SystemExit(exit_code)

        except FileNotFoundError as e:
            user_output(click.style("❌ Error: ", fg="red") + str(e))
            raise SystemExit(1) from None
