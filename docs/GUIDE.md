# Workstack Documentation

**Welcome!** This directory contains detailed documentation for the workstack project.

---

## For AI Agents: Start Here

Choose your starting point based on your task:

| Your Task                           | Start Here                                                                |
| ----------------------------------- | ------------------------------------------------------------------------- |
| **First time working on workstack** | [../CLAUDE.md](../CLAUDE.md) - Core coding standards                      |
| **Need code examples**              | [PATTERNS.md](PATTERNS.md) - Code patterns and examples                   |
| **Working with exceptions**         | [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Exception handling guide |
| **Writing tests**                   | [../tests/CLAUDE.md](../tests/CLAUDE.md) - Testing patterns               |
| **Publishing to PyPI**              | [PUBLISHING.md](PUBLISHING.md) - Publishing guide                         |
| **Project overview**                | [../README.md](../README.md) - Getting started                            |

---

## Documentation Structure

### 📋 Core Standards (Start here)

**[../CLAUDE.md](../CLAUDE.md)** - Coding standards and rules

- Core rules (type annotations, imports, exception handling, etc.)
- Quick reference table to all other docs
- Design principles

### 📖 Detailed References

**[PATTERNS.md](PATTERNS.md)** - Code patterns and examples

- Type annotations examples
- Dependency injection pattern
- Import organization examples
- Code style (reducing nesting, etc.)
- File operations, CLI development, context managers
- Resource management

**[EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md)** - Complete exception handling guide

- LBYL vs EAFP patterns
- Critical enforcement rules
- Acceptable uses of exception handling
- Dictionary access, validation, file processing
- Anti-patterns and examples

**[PUBLISHING.md](PUBLISHING.md)** - PyPI publishing guide

- Publishing both devclikit and workstack packages
- Authentication setup and credentials
- Version management and release process
- Testing and troubleshooting

### 🧪 Testing

**[../tests/CLAUDE.md](../tests/CLAUDE.md)** - Testing patterns and practices

- Unit tests with fakes
- Integration tests with real implementations
- Testing patterns

---

## Documentation Hierarchy

```
📂 Root Level (/)
├─ CLAUDE.md ................... Core coding standards (START HERE)
├─ README.md ................... Project overview
│
📂 docs/ (You are here)
├─ GUIDE.md .................... This file - documentation index
├─ PATTERNS.md ................. Code examples and patterns
└─ EXCEPTION_HANDLING.md ....... Complete exception guide
│
📂 tests/
└─ CLAUDE.md ................... Testing patterns and practices
```

---

## Navigation Flow

### Typical Workflows

**1. First-time contributor:**

```
../CLAUDE.md (core rules)
  └─> PATTERNS.md (see examples)
      └─> ../tests/CLAUDE.md (learn testing)
```

**2. Working with exceptions:**

```
../CLAUDE.md#exception-handling (rules)
  └─> EXCEPTION_HANDLING.md (complete guide)
      └─> PATTERNS.md (related examples)
```

**3. Understanding a pattern:**

```
../CLAUDE.md (read rule)
  └─> PATTERNS.md#specific-pattern (see example)
```

---

## Quick Links

### Most Referenced Documents

1. [../CLAUDE.md](../CLAUDE.md) - Core standards (read first!)
2. [PATTERNS.md](PATTERNS.md) - Code examples
3. [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Exception guide
4. [../tests/CLAUDE.md](../tests/CLAUDE.md) - Testing guide
5. [PUBLISHING.md](PUBLISHING.md) - Publishing to PyPI

### By Topic

**Writing code:**

- [../CLAUDE.md](../CLAUDE.md) - Coding standards
- [PATTERNS.md](PATTERNS.md) - Examples
- [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Exception rules

**Testing:**

- [../tests/CLAUDE.md](../tests/CLAUDE.md) - Testing patterns

**Publishing:**

- [PUBLISHING.md](PUBLISHING.md) - Publishing to PyPI

---

## Documentation Maintenance

### Keeping Docs Up-to-Date

When making changes to the codebase:

1. **Update PATTERNS.md** - If you add new patterns or examples
2. **Update EXCEPTION_HANDLING.md** - If exception handling patterns change
3. **Update tests/CLAUDE.md** - If testing patterns change
4. **Update CLAUDE.md** - If core rules change

### Review Checklist

During code review, verify:

- [ ] Examples in PATTERNS.md still compile and follow current patterns
- [ ] EXCEPTION_HANDLING.md reflects current exception handling approach
- [ ] tests/CLAUDE.md matches current testing practices
- [ ] Links in all docs point to files that exist

---

## Contributing to Documentation

Documentation improvements are welcome! When updating docs:

1. **Keep it concise** - AI agents prefer brief, scannable content
2. **Use examples** - Code examples are worth a thousand words
3. **Link liberally** - Cross-reference related docs
4. **Maintain hierarchy** - Rules in CLAUDE.md, examples in PATTERNS.md
5. **Update navigation** - Keep quick reference tables current
6. **Only link to existing files** - Verify all links work

---

## Questions?

If you can't find what you need:

1. Check [PATTERNS.md](PATTERNS.md) for code examples
2. Check [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) for exception handling details
3. Check [../tests/CLAUDE.md](../tests/CLAUDE.md) for testing guidance
4. Read [../CLAUDE.md](../CLAUDE.md) for core rules

Still stuck? The documentation may need improvement - consider opening an issue or PR.

---

## Future Documentation (Planned)

These documents have been planned but not yet implemented:

- **guides/ADDING_A_COMMAND.md** - Step-by-step command guide
- **guides/ADDING_AN_OPS_INTERFACE.md** - Step-by-step ops interface guide
- **COMMON_TASKS.md** - FAQ and common tasks

Note: ARCHITECTURE.md and FEATURE_INDEX.md now exist in the `.agent/` directory, and GLOSSARY.md is at the root level.

---

**Last updated**: 2025-10-08 (Documentation restructure - moved to .agent/ directory)
