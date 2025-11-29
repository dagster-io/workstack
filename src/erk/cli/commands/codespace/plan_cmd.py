"""Create a Codespace and open SSH session for remote planning."""

import json
import os
import subprocess
import time

import click
from erk_shared.output.output import user_output


def _print_command(cmd: list[str]) -> None:
    """Print a command with nice formatting."""
    formatted = " ".join(cmd)
    user_output(click.style("$ ", fg="cyan") + click.style(formatted, fg="white", bold=True))


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, printing it first with nice formatting."""
    _print_command(cmd)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def _get_repo_name() -> str:
    """Get the current repository's name with owner.

    Returns:
        Repository name in 'owner/repo' format.

    Raises:
        SystemExit: If gh command fails or repo info cannot be retrieved.
    """
    result = _run_command(["gh", "repo", "view", "--json", "nameWithOwner"])

    if result.returncode != 0:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to get repository info.\n\n"
            + "Make sure you're in a GitHub repository and authenticated:\n"
            + "  gh auth status"
        )
        raise SystemExit(1)

    data = json.loads(result.stdout)
    repo_name = data.get("nameWithOwner")
    if not repo_name:
        user_output(
            click.style("Error: ", fg="red") + "Could not determine repository name from gh output."
        )
        raise SystemExit(1)

    return repo_name


def _create_codespace(repo: str, description: str) -> str:
    """Create a new GitHub Codespace.

    Args:
        repo: Repository name in 'owner/repo' format.
        description: Description for the Codespace.

    Returns:
        Name of the created Codespace.

    Raises:
        SystemExit: If Codespace creation fails.
    """
    display_name = f"plan: {description}" if description else "plan"

    cmd = [
        "gh",
        "codespace",
        "create",
        "-R",
        repo,
        "-d",
        display_name,
        "--idle-timeout",
        "30m",
    ]
    result = _run_command(cmd)

    if result.returncode != 0:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to create Codespace.\n\n"
            + f"Details: {result.stderr}\n\n"
            + "Make sure GitHub Codespaces is enabled for your account:\n"
            + "  https://github.com/settings/codespaces"
        )
        raise SystemExit(1)

    codespace_name = result.stdout.strip()
    if not codespace_name:
        user_output(click.style("Error: ", fg="red") + "Codespace creation returned empty name.")
        raise SystemExit(1)

    return codespace_name


def _wait_for_codespace(codespace_name: str, timeout_seconds: int = 300) -> None:
    """Wait for Codespace to become available.

    Args:
        codespace_name: Name of the Codespace to wait for.
        timeout_seconds: Maximum time to wait in seconds.

    Raises:
        SystemExit: If Codespace doesn't become available within timeout.
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            user_output(
                click.style("Error: ", fg="red")
                + f"Codespace did not become available within {timeout_seconds} seconds."
            )
            raise SystemExit(1)

        result = _run_command(["gh", "codespace", "list", "--json", "name,state"])

        if result.returncode != 0:
            # Retry on transient errors
            time.sleep(2)
            continue

        codespaces = json.loads(result.stdout)
        for cs in codespaces:
            if cs.get("name") == codespace_name:
                state = cs.get("state", "")
                if state == "Available":
                    return
                # Still waiting
                break

        time.sleep(3)


@click.command("plan")
@click.argument("description", required=False, default="")
def plan_codespace(description: str) -> None:
    """Create a Codespace and open SSH session for remote planning.

    Creates a new GitHub Codespace for the current repository, waits for
    it to become available, then opens an SSH connection.

    Once connected, run:
      claude "/erk:craft-plan <description>"

    DESCRIPTION is an optional description for what you're planning.
    """
    # Get repository info
    repo = _get_repo_name()

    user_output("Creating Codespace for planning...")
    codespace_name = _create_codespace(repo, description)
    user_output(f"Codespace '{codespace_name}' created, waiting for ready...")

    _wait_for_codespace(codespace_name)
    user_output(click.style("✓ ", fg="green") + "Codespace ready.")
    user_output("")
    user_output("Once connected, run:")
    if description:
        user_output(f'  claude "/erk:craft-plan {description}"')
    else:
        user_output('  claude "/erk:craft-plan <description>"')
    user_output("")
    user_output("Connecting via SSH...")

    # Replace current process with SSH to Codespace
    ssh_cmd = ["gh", "codespace", "ssh", "-c", codespace_name]
    _print_command(ssh_cmd)
    os.execvp("gh", ssh_cmd)
    # Never returns - process is replaced
