# Python Example Sandbox Template
#
# This is a template showing common customization patterns for Python projects.
# To use: Copy this directory to `.erk/sandboxes/<your-sandbox-name>/` and customize.
#
# CUSTOMIZATION EXAMPLES (uncomment and modify as needed):

# Option 1: Use different Python version
# FROM python:3.11-slim
# FROM python:3.12-slim
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    build-essential \
    # OPTIONAL: Add more system packages
    # postgresql-client \
    # nodejs \
    # redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Claude Code CLI
RUN curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh | sh

# OPTIONAL: Pre-install project dependencies for faster startup
# Uncomment if you want dependencies baked into image (slower builds, faster runs)
# COPY pyproject.toml uv.lock ./
# RUN uv sync --frozen --no-dev

# OPTIONAL: Install additional Python tools
# RUN uv tool install black
# RUN uv tool install mypy
# RUN uv tool install pytest-watch

# OPTIONAL: Add Node.js (useful for full-stack projects)
# RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
#     && apt-get install -y nodejs

# OPTIONAL: Add database clients
# RUN apt-get update && apt-get install -y \
#     postgresql-client \
#     mysql-client \
#     sqlite3

# Set working directory (worktree will be mounted here)
WORKDIR /workspace

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1
    # OPTIONAL: Add more environment variables
    # DATABASE_URL=postgresql://localhost/testdb \
    # REDIS_URL=redis://localhost:6379

# OPTIONAL: Expose ports if running services
# EXPOSE 8000
# EXPOSE 5432

# Entrypoint: Interactive shell by default
CMD ["/bin/bash"]

# CUSTOMIZATION NOTES:
#
# 1. Base Image:
#    - Use python:X.Y-slim for smaller images
#    - Use python:X.Y for full image with more tools
#    - Use python:X.Y-alpine for smallest size (may need different apt commands)
#
# 2. Caching Strategy:
#    - Copy dependency files BEFORE source code
#    - Docker caches layers, so dependency installs only re-run when files change
#    - Example: COPY pyproject.toml uv.lock before COPY . .
#
# 3. Multi-Stage Builds:
#    - Use multiple FROM statements to separate build and runtime stages
#    - Example: Build wheels in one stage, copy to slim runtime stage
#    - Reduces final image size significantly
#
# 4. Security:
#    - Don't copy secrets into image (use env vars at runtime)
#    - Use specific versions instead of :latest for reproducibility
#    - Run as non-root user for production (add USER statement)
#
# 5. Performance:
#    - Keep frequently changing layers at the bottom
#    - Combine RUN commands to reduce layer count
#    - Use .dockerignore to exclude unnecessary files from build context
