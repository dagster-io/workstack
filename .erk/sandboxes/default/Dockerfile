# Default Sandbox for Erk Docker-Based Implementation
#
# This Dockerfile creates an isolated environment for running Claude Code CLI
# to execute implementation plans (`/erk:implement-plan`) inside ephemeral containers.
#
# Base Image: python:3.13-slim
# - Matches erk's Python version requirement (3.13+)
# - Slim variant keeps image size smaller while including necessary build tools
FROM python:3.13-slim

# Install system dependencies
# - git: Required for git operations (commits, status checks)
# - openssh-client: Required for SSH-based git authentication (GitHub, GitLab)
# - curl: Required for downloading Claude Code CLI installer
# - build-essential: Required for compiling Python packages with native extensions
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
# - Used by erk for dependency management
# - Faster alternative to pip
# - Installation: copy from official uv Docker image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Claude Code CLI
# - Required for executing `/erk:implement-plan` command
# - Installation method: download from official Anthropic distribution
# - The installer script handles platform detection and installation
RUN curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh | sh

# Set working directory
# - Volume mount expectation: Host worktree will be mounted at /workspace
# - All operations happen relative to this directory
WORKDIR /workspace

# Environment variables
# - PYTHONUNBUFFERED: Ensure Python output is not buffered (see logs in real-time)
# - UV_SYSTEM_PYTHON: Tell uv to use system Python instead of creating virtualenv
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Credential mounting expectations (configured at runtime):
# - Git config: ~/.gitconfig (read-only mount)
# - SSH keys: ~/.ssh (read-only mount)
# - These are mounted when container runs, not built into image

# Entrypoint: Interactive shell by default
# - Allows Claude Code CLI to run interactively with proper TTY
# - Container is ephemeral: created on start, destroyed on completion
CMD ["/bin/bash"]
