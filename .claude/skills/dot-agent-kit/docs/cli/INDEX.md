# cli/ - Shared CLI Utilities

## Overview

This directory contains shared utilities used by all CLI commands for consistent output formatting and behavior.

## Files

### list_formatting.py

[→ Full docs](list_formatting.md)

Shared list output formatting functions (8 total) for badges, headers, colors, and alignment.

**Used by**: All list commands (artifact, hook, kit)

### output.py

Output routing to appropriate streams (stdout vs stderr).

**Key functions**:

- `user_output()` - Routes to stderr (human-readable output)
- `machine_output()` - Routes to stdout (machine-parseable data)

### colors.py

ANSI color code definitions used throughout the CLI.

## Navigation

- **Need complete API reference?** → Load [list_formatting.md](list_formatting.md)
- **See usage in commands?** → Load [../commands/artifact/list.md](../commands/artifact/list.md) (example)
- **Back to package overview?** → Load [../INDEX.md](../INDEX.md)
