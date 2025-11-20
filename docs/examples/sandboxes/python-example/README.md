# Python Example Sandbox Template

This directory contains an example sandbox template showing common customization patterns for Python projects. Use it as a starting point for creating your own custom sandboxes.

## How to Use This Template

1. **Copy to your sandboxes directory**:

   ```bash
   cp -r docs/examples/sandboxes/python-example .erk/sandboxes/my-project
   ```

2. **Customize the Dockerfile** for your project needs (see examples below)

3. **Update the README** to document your sandbox's purpose and configuration

4. **Use with erk**: Run `erk implement --docker` (will use default sandbox for now)

   Future: `erk implement --docker --sandbox my-project`

## Common Customization Patterns

### Different Python Version

```dockerfile
# Use Python 3.11 instead of 3.13
FROM python:3.11-slim
```

### Add Node.js for Full-Stack Projects

```dockerfile
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs
```

### Add Database Client

```dockerfile
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
```

### Pre-Install Project Dependencies

```dockerfile
# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen means use exact versions from lock file)
RUN uv sync --frozen --no-dev
```

**Trade-off**: Slower image builds, faster container startup

### Multi-Stage Build (Smaller Image)

```dockerfile
# Stage 1: Build dependencies
FROM python:3.13 AS builder
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Stage 2: Runtime (slim)
FROM python:3.13-slim
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /workspace
CMD ["/bin/bash"]
```

**Benefit**: Smaller final image (no build tools included)

### Add Custom Environment Variables

```dockerfile
ENV DATABASE_URL=postgresql://localhost/testdb \
    REDIS_URL=redis://localhost:6379 \
    DEBUG=1
```

### Run as Non-Root User (Security)

```dockerfile
# Create non-root user
RUN useradd -m -u 1000 devuser

# Switch to non-root user
USER devuser

WORKDIR /workspace
```

**Benefit**: Better security (container can't modify root-owned files)

## Real-World Examples

### Web Application (Django/FastAPI)

```dockerfile
FROM python:3.13-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install tools
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh | sh

# Pre-install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

WORKDIR /workspace
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    DATABASE_URL=postgresql://localhost/testdb

EXPOSE 8000
CMD ["/bin/bash"]
```

### Data Science Project

```dockerfile
FROM python:3.13

# System dependencies including scientific computing libraries
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install tools
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh | sh

# Pre-install common data science packages
RUN uv pip install \
    numpy \
    pandas \
    scikit-learn \
    jupyter

WORKDIR /workspace
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

EXPOSE 8888
CMD ["/bin/bash"]
```

### Monorepo with Multiple Packages

```dockerfile
FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN curl -fsSL https://raw.githubusercontent.com/anthropics/claude-code/main/install.sh | sh

# Install dependencies for all packages in monorepo
WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY packages/package-a/pyproject.toml packages/package-a/
COPY packages/package-b/pyproject.toml packages/package-b/
RUN uv sync --frozen --all-packages

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

CMD ["/bin/bash"]
```

## Dockerfile Best Practices

### Layer Caching

Order matters! Put rarely changing layers at the top:

```dockerfile
# ✅ GOOD: Dependencies cached separately from code
FROM python:3.13-slim
RUN apt-get update && apt-get install -y git  # Cached
COPY pyproject.toml ./                         # Cached if unchanged
RUN uv sync --frozen                           # Cached if dependencies unchanged
COPY . .                                        # Only this re-runs on code changes

# ❌ BAD: Code changes invalidate dependency cache
FROM python:3.13-slim
COPY . .                                        # Everything below re-runs on ANY change
RUN apt-get update && apt-get install -y git
RUN uv sync --frozen
```

### Combine Commands

Reduce layer count by combining RUN statements:

```dockerfile
# ✅ GOOD: Single layer
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ❌ BAD: Multiple layers
RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*
```

### Use .dockerignore

Create `.dockerignore` to exclude unnecessary files from build context:

```
# .dockerignore
__pycache__/
*.pyc
.git/
.erk/
.venv/
node_modules/
.pytest_cache/
*.log
```

**Benefit**: Faster builds, smaller context

## Architecture Notes

### Multi-Sandbox Support

Erk supports multiple sandboxes per repository:

- **Structure**: `.erk/sandboxes/<sandbox-name>/`
- **Convention**: Sandbox name typically matches package name
- **Current**: Only "default" sandbox is used
- **Future**: `--sandbox <name>` flag to select specific sandbox

### Why Separate from .erk/sandboxes/?

This template lives in `docs/examples/sandboxes/` (not `.erk/sandboxes/`) to:

- Avoid polluting the actual sandbox namespace
- Prevent accidental use of example templates
- Provide clear separation between templates and configured sandboxes

## See Also

- `.erk/sandboxes/default/` - The default sandbox configuration
- `docs/docker-sandboxes.md` - Comprehensive sandbox documentation
- `docs/agent/docker-implementation.md` - Agent guide for Docker features
