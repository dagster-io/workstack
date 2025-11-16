# Skill-Based Documentation Example

This directory demonstrates automatic documentation extraction from a Claude Code session.

## Structure

```
dot-agent-kit/                          ← One skill per package
├── SKILL.md                            ← Entry point (~1.5K tokens)
└── docs/                               ← Mirrors src/ structure
    ├── INDEX.md                        ← Package overview (~1K tokens)
    ├── commands/
    │   ├── INDEX.md                    ← Commands overview (~2K tokens)
    │   └── artifact/
    │       ├── INDEX.md                ← Directory overview (~1.5K tokens)
    │       └── list.md                 ← File docs (~2.5K tokens)
    └── cli/
        ├── INDEX.md                    ← CLI utilities overview (~1K tokens)
        └── list_formatting.md          ← File docs (~3K tokens)
```

## Key Principles

1. **Spatial awareness** - Docs mirror code structure
2. **Progressive disclosure** - Load only what's relevant
3. **Hierarchical navigation** - INDEX.md at each level
4. **One skill per package** - Separate scope per package

## Token Budget Examples

- Working on single file: ~4K tokens
- Adding new feature: ~10K tokens
- Unrelated work: ~1.5K tokens (just SKILL.md)

Compare to monolithic docs: 15-30K tokens always loaded.
