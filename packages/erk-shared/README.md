# erk-shared

Shared utilities and interfaces for erk and dot-agent-kit packages.

This package provides:

- **GitHub Issues Interface**: ABC with Real/Fake implementations
- **Naming Utilities**: Filename and worktree name transformations
- **Metadata Blocks**: GitHub comment formatting utilities
- **Impl Folder Utilities**: Issue reference management and progress parsing

## Purpose

This package exists to break the circular dependency between `erk` and `dot-agent-kit`:

- `erk` imports kit utilities from `dot-agent-kit`
- `dot-agent-kit` imports interfaces and utilities from `erk`

By extracting shared code to `erk-shared`, we create an acyclic dependency graph:

```
erk-shared (no dependencies)
    ↑
    |
dot-agent-kit (depends on: erk-shared)
    ↑
    |
erk (depends on: dot-agent-kit, erk-shared)
```

## Note

This is an internal workspace package, not published to PyPI.
