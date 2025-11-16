# commands/ - CLI Command Implementations

## Overview

This directory contains all CLI command implementations for dot-agent-kit, organized by domain.

## Directory Structure

```
commands/
├── artifact/      → Artifact management (list, install, remove)
├── hook/          → Hook management (list, install, remove)
├── kit/           → Kit operations (list, search, install, update)
├── md/            → Markdown utilities (generate, lint)
├── run/           → Run kit CLI commands
├── status.py      → Show managed/unmanaged status
├── check.py       → Check artifact installations
└── init.py        → Initialize dot-agent configuration
```

## Subdirectories

### artifact/

[→ INDEX](artifact/INDEX.md)

Commands for managing Claude artifacts (skills, commands, agents, hooks, docs).

**Key operations**: list/ls, install, remove, show

### hook/

[→ INDEX](hook/INDEX.md)

Commands for managing lifecycle hooks.

**Key operations**: list/ls, install, remove

### kit/

[→ INDEX](kit/INDEX.md)

Commands for working with kits (collections of artifacts).

**Key operations**: list/ls, search, install, update, remove

### md/

Markdown utilities for generating and linting documentation.

**Key operations**: generate, lint

### run/

Run kit-provided CLI commands.

**Key operations**: execute kit CLI commands

## Root-Level Commands

### status.py

Shows managed vs unmanaged artifact status.

### check.py

Checks artifact installation integrity.

### init.py

Initializes dot-agent configuration.

## Navigation

- **Working in artifact/?** → Load [artifact/INDEX.md](artifact/INDEX.md)
- **Working in hook/?** → Load [hook/INDEX.md](hook/INDEX.md)
- **Working in kit/?** → Load [kit/INDEX.md](kit/INDEX.md)
- **Need formatting utilities?** → Load [../cli/list_formatting.md](../cli/list_formatting.md)
- **Back to package overview?** → Load [../INDEX.md](../INDEX.md)
