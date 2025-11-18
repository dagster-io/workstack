"""Docker orchestration for executing implementation plans in containers.

This module orchestrates Docker-based plan execution:
- Build Docker images from sandbox Dockerfiles
- Configure volume mounts (worktree + credentials)
- Run Claude Code CLI inside ephemeral containers
- Handle cleanup and error recovery

Follows LBYL philosophy: check conditions before acting, let exceptions bubble.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.ops.docker import Docker


@dataclass(frozen=True)
class DockerConfig:
    """Configuration for Docker-based implementation.

    Immutable configuration object containing all parameters needed to run
    Claude Code CLI in a Docker container.

    Attributes:
        image_tag: Docker image tag to use (e.g., "erk-implement:abc123")
        volumes: Volume mount mappings (host_path:container_path)
        env_vars: Environment variables to set in container
        dockerfile_path: Path to Dockerfile in sandbox
        sandbox_name: Name of sandbox (currently always "default")
    """

    image_tag: str
    volumes: dict[str, str]
    env_vars: dict[str, str]
    dockerfile_path: Path
    sandbox_name: str


def build_implementation_image(
    docker: Docker,
    worktree_root: Path,
    sandbox_name: str = "default",
) -> str:
    """Build Docker image for implementation execution.

    LBYL checks:
    - Validates sandbox Dockerfile exists
    - Docker daemon running checked by caller

    Args:
        docker: Docker operations interface
        worktree_root: Root directory of worktree (used as build context)
        sandbox_name: Name of sandbox to use (default: "default")

    Returns:
        Image tag string (e.g., "erk-implement:abc123")

    Raises:
        FileNotFoundError: If sandbox Dockerfile doesn't exist
        RuntimeError: If Docker build fails
    """
    # LBYL: Check Dockerfile exists before building
    dockerfile_path = worktree_root / ".erk" / "sandboxes" / sandbox_name / "Dockerfile"
    if not dockerfile_path.exists():
        raise FileNotFoundError(
            f"Sandbox Dockerfile not found: {dockerfile_path}\n"
            f"Create .erk/sandboxes/{sandbox_name}/Dockerfile first.\n"
            f"See docs/examples/sandboxes/ for templates."
        )

    # Generate unique image tag from worktree name and timestamp
    import time

    worktree_name = worktree_root.name
    timestamp = int(time.time())
    image_tag = f"erk-implement-{worktree_name}:{timestamp}"

    # Build image with worktree as build context
    docker.build_image(
        dockerfile_path=dockerfile_path,
        tag=image_tag,
        build_context=worktree_root,
    )

    return image_tag


def setup_container_volumes(worktree_root: Path) -> dict[str, str]:
    """Configure volume mounts for Docker container.

    Mounts:
    - Current worktree at /workspace (read-write)
    - Git config at ~/.gitconfig (read-only)
    - SSH directory at ~/.ssh (read-only)

    LBYL checks:
    - Uses absolute paths (Docker requirement)
    - Validates worktree_root exists

    Args:
        worktree_root: Root directory of worktree to mount

    Returns:
        Dictionary of volume mounts (host_path:container_path:options)

    Raises:
        FileNotFoundError: If worktree_root doesn't exist
    """
    # LBYL: Check worktree exists
    if not worktree_root.exists():
        raise FileNotFoundError(f"Worktree not found: {worktree_root}")

    # Get absolute path for Docker (required by Docker CLI)
    worktree_absolute = worktree_root.resolve()

    # Setup volume mounts
    volumes: dict[str, str] = {
        # Mount worktree (read-write for implementation changes)
        str(worktree_absolute): "/workspace",
    }

    # Mount git config (read-only) if exists
    home = Path.home()
    gitconfig = home / ".gitconfig"
    if gitconfig.exists():
        volumes[str(gitconfig.resolve())] = "/root/.gitconfig:ro"

    # Mount SSH directory (read-only) if exists
    ssh_dir = home / ".ssh"
    if ssh_dir.exists():
        volumes[str(ssh_dir.resolve())] = "/root/.ssh:ro"

    return volumes


def run_claude_in_container(
    docker: Docker,
    config: DockerConfig,
) -> int:
    """Run Claude Code CLI inside Docker container.

    Executes `/erk:implement-plan` command in container with:
    - Interactive TTY attached
    - Volume mounts configured
    - Environment variables set
    - Automatic cleanup on completion

    LBYL checks:
    - Docker daemon running checked by caller
    - Volume paths validated by docker_ops

    Args:
        docker: Docker operations interface
        config: Docker configuration (image, volumes, env vars)

    Returns:
        Exit code from Claude Code CLI execution

    Raises:
        RuntimeError: If container execution fails
        OSError: If Docker daemon not running
    """
    # Build command to execute in container
    # Note: Using 'claude' command directly - assumes Claude Code CLI installed in image
    command = [
        "claude",
        "--permission-mode",
        "acceptEdits",
        "/erk:implement-plan",
    ]

    # Run container interactively
    # Container is ephemeral (--rm flag in docker.run_container)
    exit_code = docker.run_container(
        image_tag=config.image_tag,
        volumes=config.volumes,
        env_vars=config.env_vars,
        command=command,
        interactive=True,
    )

    return exit_code


def execute_docker_implementation(
    docker: Docker,
    worktree_root: Path,
    sandbox_name: str = "default",
) -> int:
    """Execute implementation plan in Docker container (main entry point).

    This is the main orchestration function that:
    1. Checks Docker daemon is running
    2. Builds Docker image from sandbox Dockerfile
    3. Configures volume mounts and environment
    4. Runs Claude Code CLI in container
    5. Returns exit code

    LBYL checks:
    - Docker daemon running
    - Worktree has .plan/plan.md
    - Sandbox Dockerfile exists

    Args:
        docker: Docker operations interface
        worktree_root: Root directory of worktree
        sandbox_name: Name of sandbox to use (default: "default")

    Returns:
        Exit code from Claude Code CLI

    Raises:
        RuntimeError: If Docker daemon not running
        FileNotFoundError: If plan.md or Dockerfile missing
    """
    # LBYL: Check Docker daemon running first
    if not docker.is_daemon_running():
        raise RuntimeError(
            "Docker daemon not running.\nStart Docker Desktop or run: sudo systemctl start docker"
        )

    # LBYL: Check plan exists before any Docker operations
    plan_file = worktree_root / ".plan" / "plan.md"
    if not plan_file.exists():
        raise FileNotFoundError(
            f"No plan found: {plan_file}\nRun /erk:persist-plan to create a plan first."
        )

    # Build Docker image
    image_tag = build_implementation_image(
        docker=docker,
        worktree_root=worktree_root,
        sandbox_name=sandbox_name,
    )

    # Setup volume mounts
    volumes = setup_container_volumes(worktree_root=worktree_root)

    # Configure environment variables
    env_vars: dict[str, str] = {
        "PYTHONUNBUFFERED": "1",  # Ensure Python output is not buffered
    }

    # Create configuration
    dockerfile_path = worktree_root / ".erk" / "sandboxes" / sandbox_name / "Dockerfile"
    config = DockerConfig(
        image_tag=image_tag,
        volumes=volumes,
        env_vars=env_vars,
        dockerfile_path=dockerfile_path,
        sandbox_name=sandbox_name,
    )

    # Run Claude Code CLI in container
    exit_code = run_claude_in_container(docker=docker, config=config)

    return exit_code
