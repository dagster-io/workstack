## Purpose

This directory contains the kit registry system for dot-agent-kit, which manages reusable agent components (agents, commands, skills) that extend AI assistant capabilities.

The kit registry provides:

- **Structured catalog** of installed kits and their capabilities
- **Machine-readable format** for AI assistants to discover available functionality
- **Auto-generated documentation** maintained by `dot-agent kit` commands

## For AI Assistants

Load the kit registry to discover what functionality is available in this project:

```markdown
@.agent/kits/kit-registry.md
```

The registry will expand to show all installed kits with references to their individual documentation. Each kit entry provides information about available agents, commands, and skills.

## For Developers

Manage kits using `dot-agent kit` commands:

- `dot-agent kit list` - Show installed kits
- `dot-agent kit install <kit-id>` - Install a kit
- `dot-agent kit sync` - Regenerate registry from installed kits

## Maintenance

The `kit-registry.md` file and individual `registry-entry.md` files are auto-generated. Do not edit them manually - changes will be overwritten by `dot-agent kit sync`.
