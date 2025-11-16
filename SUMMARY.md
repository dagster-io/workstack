# Skill-Based Documentation System - Complete Example

## What You're Looking At

This directory contains a **working example** of automatically generated documentation from a Claude Code session that analyzed CLI list formatting standards.

## The Session

**Input**: Claude Code session analyzing dot-agent-kit list commands
**Output**: Hierarchical, spatially-aware documentation skill

**Session knowledge extracted**:
- 4 list commands with detailed features
- 8 shared formatting functions
- Consistent implementation patterns
- Color schemes and design standards

## The Generated Structure

```
dot-agent-kit/
├── SKILL.md                                    ← Entry point with navigation
└── docs/
    ├── INDEX.md                                ← Package overview
    ├── commands/
    │   ├── INDEX.md                            ← Commands overview  
    │   └── artifact/
    │       ├── INDEX.md                        ← Directory overview
    │       └── list.md                         ← File documentation
    └── cli/
        ├── INDEX.md                            ← CLI utilities overview
        └── list_formatting.md                  ← File documentation
```

## Key Innovation: Hierarchical INDEX Files

Every directory has an INDEX.md that provides:
1. Overview of what's at this level
2. Quick reference for common needs
3. Navigation to deeper content
4. Links back to parent context

This solves the "chicken and egg" problem - agents know where to navigate without loading everything.

## Token Budget Comparison

**Traditional monolithic docs**: 15-30K tokens (always loaded)

**This system**:
- Working on single file: ~4K tokens
- Adding new feature: ~10K tokens  
- Unrelated work: ~1.5K tokens

**Savings**: 60-95% reduction in typical cases

## Files to Review

Start here to understand the system:

1. **dot-agent-kit/SKILL.md** - Entry point, explains navigation
2. **dot-agent-kit/docs/INDEX.md** - Package overview
3. **dot-agent-kit/docs/commands/INDEX.md** - Patterns and structure
4. **dot-agent-kit/docs/commands/artifact/list.md** - Detailed file docs

## How This Would Work in Practice

### Agent working on artifact/list.py

```python
# Auto-detection
cwd = "packages/dot-agent-kit/src/dot_agent_kit/commands/artifact"
file = "list.py"

# SKILL.md tells agent what to load
load("dot-agent-kit/docs/commands/artifact/list.md")

# Token usage: ~4K tokens
```

### Agent adding new list command

```python
# Task detected: adding new functionality
task = "add new list command"

# SKILL.md guides progressive loading
load("dot-agent-kit/docs/INDEX.md")          # Overview
load("dot-agent-kit/docs/commands/INDEX.md") # Patterns
load("dot-agent-kit/docs/commands/artifact/list.md")  # Example
load("dot-agent-kit/docs/cli/list_formatting.md")     # Utilities

# Token usage: ~10K tokens
```

## Next Steps to Implement

1. **Build extraction pipeline** - Parse session JSON-L files
2. **Map knowledge to files** - Identify source file references
3. **Generate hierarchy** - Create INDEX.md at each level
4. **Create session hook** - Trigger on session completion
5. **Refine templates** - Improve generated doc quality

## Why This Matters

### Scales to Any Project Size

- 10 files or 10,000 files
- Simple CLI or complex distributed system
- Single package or monorepo

### Token Budget Stays Manageable

Agent loads 1-10K tokens instead of 15-100K+

### Documentation Stays Fresh

Automatically updated from sessions, never stale

### Progressive Disclosure

Agent learns incrementally, not all at once

## The Vision

Every Claude Code session becomes an opportunity to:
1. Extract discovered knowledge
2. Map to code structure
3. Update documentation automatically
4. Accumulate project intelligence over time

Documentation becomes a **living artifact** that grows with your codebase.
