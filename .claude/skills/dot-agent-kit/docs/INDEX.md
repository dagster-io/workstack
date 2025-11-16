# dot-agent-kit Package

## Overview

The dot-agent-kit package provides CLI commands and utilities for managing Claude Code artifacts (skills, commands, agents, hooks) through a kit system.

## Package Structure

```
dot-agent-kit/
├── commands/          → CLI command implementations
├── cli/               → Shared CLI utilities (formatting, output)
├── hooks/             → Hook system infrastructure
├── data/              → Bundled kits and artifact data
└── core.py            → Core logic and interfaces
```

## Subdirectories

### commands/

[→ INDEX](commands/INDEX.md)

CLI command implementations organized by domain (artifact, hook, kit, md, run).

**Contains**: Command groups for managing artifacts, hooks, kits, markdown utilities, and kit CLI runners.

### cli/

[→ INDEX](cli/INDEX.md)

Shared CLI utilities for consistent command-line experience.

**Contains**: Formatting functions, output routing, and shared CLI helpers.

### hooks/

Hook system infrastructure for lifecycle events.

**Contains**: Hook registration, execution, and management logic.

### data/

Bundled kits and artifact data.

**Contains**: Default kits, artifact manifests, and registry data.

## Navigation

- **Working in commands/?** → Load [commands/INDEX.md](commands/INDEX.md)
- **Working in cli/?** → Load [cli/INDEX.md](cli/INDEX.md)
- **Working on specific file?** → Load the corresponding `.md` file (e.g., `commands/artifact/list.md`)
