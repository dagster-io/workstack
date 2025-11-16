# commands/artifact/ - Artifact Management Commands

## Overview

This directory implements commands for managing Claude Code artifacts (skills, commands, agents, hooks, docs).

## Files

### list.py / ls.py

[→ Full docs](list.md)

List installed artifacts with filtering by level, type, and source.

**Key features**: Level filtering (--user/--project), type filtering (--type), managed-only filter (--managed), two-section layout, compact/verbose views

### formatting.py

[→ Full docs](formatting.md)

Artifact-specific output formatting functions (5 total).

**Used by**: list.py for compact and verbose output formatting

## Navigation

- **Modifying list output?** → Load [list.md](list.md)
- **Adding artifact formatter?** → Load [formatting.md](formatting.md)
- **Need shared utilities?** → Load [../../cli/list_formatting.md](../../cli/list_formatting.md)
- **Back to commands overview?** → Load [../INDEX.md](../INDEX.md)
