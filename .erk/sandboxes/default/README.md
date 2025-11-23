# Default Sandbox

## Purpose

This sandbox provides a default Python development environment for running `erk implement --docker`. It includes Claude Code CLI and common development tools needed to execute implementation plans in isolation.

## What's Included

- **Python 3.13**: Matches erk's version requirement
- **Claude Code CLI**: For executing `/erk:implement-plan` command
- **uv**: Fast Python package manager used by erk
- **git**: For version control operations (commits, branches)
- **SSH client**: For GitHub/GitLab authentication

## When to Use

Use this sandbox when you want to:

- Execute implementation plans in isolation from your host environment
- Test changes without affecting your local setup
- Ensure reproducible builds across different machines
- Work with potentially unstable or experimental changes

## How It Works

When you run `erk implement --docker`:

1. **Image Build**: Docker builds an image from this Dockerfile (cached after first build)
2. **Volume Mount**: Your current worktree is mounted at `/workspace` (read-write)
3. **Credentials**: Git config and SSH keys are mounted read-only from your home directory
4. **Execution**: Claude Code CLI runs `/erk:implement-plan` inside the container
5. **Cleanup**: Container is destroyed automatically when done

## Customization

To customize this sandbox for your project needs:

1. **Copy this directory** to a new sandbox (e.g., `.erk/sandboxes/my-project/`)
2. **Modify the Dockerfile**:
   - Change base image (e.g., `python:3.11` for older Python)
   - Add project-specific dependencies
   - Install additional tools (e.g., `nodejs`, `postgres`)
3. **Update this README** to document your changes
4. **Use with flag** (future): `erk implement --docker --sandbox my-project`

## Common Customizations

### Add Node.js

```dockerfile
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs
```

### Add PostgreSQL Client

```dockerfile
RUN apt-get update && apt-get install -y postgresql-client
```

### Install Project Dependencies on Build

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
```

## Troubleshooting

### Image build fails

- **Check Dockerfile syntax**: Ensure all commands are valid
- **Check network access**: uv/pip need internet to download packages
- **Check disk space**: `docker system df` to see usage

### Container runs but Claude Code fails

- **Check credentials mounted**: Ensure git config and SSH keys are accessible
- **Check Claude Code installation**: May need to update install script
- **Check permissions**: Worktree must be readable/writable

### Performance issues on macOS

- **Volume mount slow**: Known Docker Desktop issue with large directories
- **Workaround**: Use `.dockerignore` to exclude unnecessary files
- **Alternative**: Use native mode (`erk implement` without `--docker`)

## Architecture

This sandbox is part of erk's multi-sandbox architecture:

- **Structure**: `.erk/sandboxes/<sandbox-name>/`
- **Convention**: Sandbox name typically matches package name
- **Future**: `--sandbox <name>` flag for selecting specific sandbox
- **Default**: This "default" sandbox is used when no sandbox specified

## See Also

- `docs/docker-sandboxes.md` - Comprehensive sandbox guide
- `docs/examples/sandboxes/` - Example templates for common use cases
- `docs/agent/docker-implementation.md` - Agent guide for Docker features
