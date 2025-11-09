# Documentation Guide

## Quick Navigation

The documentation is organized by audience and purpose:

### For Agents (AI Assistants)

**Python Coding Standards:**

- Load the `dignified-python` skill for all Python coding standards
- Covers: exception handling, type annotations, imports, ABC patterns, file operations, CLI development

**Workstack-Specific Documentation:**

- [glossary.md](glossary.md) - Project terminology and definitions
- [testing.md](testing.md) - Testing architecture with fakes and ops patterns

### For Humans

- [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) - Agentic programming philosophy
- [../writing/schrockn-style/](../writing/schrockn-style/) - Writing style guides
- Package READMEs (e.g., `packages/workstack-dev/README.md`)

## Documentation Structure

```
docs/
├── agent/                      # Agent-focused reference
│   ├── glossary.md            # Workstack terminology
│   ├── guide.md               # This file
│   └── testing.md             # Testing patterns
└── writing/                   # Human-readable guides
    ├── agentic-programming/
    └── schrockn-style/
```

## Task-Based Navigation

| Your Task                           | Start Here                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Understanding workstack terminology | [glossary.md](glossary.md)                                                                                     |
| Writing tests with fakes/ops        | [testing.md](testing.md)                                                                                       |
| Python coding standards             | Load `dignified-python` skill                                                                                  |
| Understanding agentic programming   | [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) |
