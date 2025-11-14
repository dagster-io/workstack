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
- [cli-architecture.md](cli-architecture.md) - CLI command architecture and dry-run implementation

### For Humans

- [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) - Agentic programming philosophy
- [../writing/schrockn-style/](../writing/schrockn-style/) - Writing style guides
- Package READMEs (e.g., `packages/workstack-dev/README.md`)

## Project Planning Files

**`.PLAN.md`** - Local implementation planning document

- Located at repository root (`.PLAN.md`)
- **In `.gitignore`** - Not tracked by git, local-only
- Used for tracking multi-phase implementation progress
- Updated as work progresses through phases
- Format: Markdown with phase/step tracking, completion status, and next steps

**Purpose**: Agents can read and update `.PLAN.md` to track implementation progress across sessions without cluttering git history with planning documents.

## Documentation Structure

```
docs/
├── agent/                      # Agent-focused reference
│   ├── cli-architecture.md    # CLI command architecture
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
| Implementing CLI commands           | [cli-architecture.md](cli-architecture.md)                                                                     |
| Python coding standards             | Load `dignified-python` skill                                                                                  |
| Understanding agentic programming   | [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) |
