---
name: layered-testing
description: This skill should be used when writing tests, fixing bugs, adding features, or modifying the ops layer. Use when you need guidance on testing architecture, working with fakes, implementing ops interfaces, or understanding the defense-in-depth testing strategy. Essential for maintaining test quality and understanding where different types of tests belong.
---

# Layered Testing Architecture for Python

**Use this skill when**: Writing tests, fixing bugs, adding features, or modifying adapter/gateway/ops layers in Python projects.

## Overview

This skill provides a **defense-in-depth testing strategy** with four layers for Python applications:

```
┌─────────────────────────────────────────┐
│  Layer 4: E2E Integration Tests (5%)   │  ← Smoke tests over real system
├─────────────────────────────────────────┤
│  Layer 3: Business Logic Tests (80%)   │  ← Tests over fakes (fast!)
├─────────────────────────────────────────┤
│  Layer 2: Adapter Implementation Tests (15%)│  ← Tests WITH mocking
├─────────────────────────────────────────┤
│  Layer 1: Fake Infrastructure Tests    │  ← Verify test doubles work
└─────────────────────────────────────────┘
```

**Philosophy**: Test business logic extensively over fast in-memory fakes. Use real implementations sparingly for integration validation.

**Terminology note**: The "adapter layer" (also called ops/gateways/providers) refers to thin wrappers around heavyweight external APIs (databases, filesystems, HTTP APIs, message queues, etc.). The pattern matters more than the name.

## Quick Decision: What Should I Read?

**Adding a feature or fixing a bug?**
→ Read `quick-reference.md` first, then `workflows.md#adding-a-new-feature`

**Need to understand where to put a test?**
→ Read `testing-strategy.md`

**Working with Python-specific patterns?**
→ Read `python-specific.md`

**Adding/changing an adapter interface?**
→ Read `ops-architecture.md`, then `workflows.md#adding-an-adapter-method`

**Need to implement a specific pattern (CliRunner, builders, etc.)?**
→ Read `patterns.md`

**Not sure if I'm doing it right?**
→ Read `anti-patterns.md`

**Just need a quick lookup?**
→ Read `quick-reference.md`

## When to Read Each Reference Document

### 📖 `ops-architecture.md`

**Read when**:

- Adding or changing adapter/gateway/ops interfaces
- Understanding the ABC/Real/Fake/DryRun pattern
- Need examples of adapter implementations
- Want to understand what adapters are (and why they're thin)

**Contents**:

- What are adapter classes? (naming: adapters/gateways/ops/providers)
- The four implementations (ABC, Real, Fake, DryRun)
- Code examples for each
- When to add/change adapter methods
- Design principles (keep adapters thin)
- Common adapter types (Database, API, FileSystem, MessageQueue)

### 📖 `testing-strategy.md`

**Read when**:

- Deciding where to put a test
- Understanding the four testing layers
- Need test distribution guidance (80/15/5 rule)
- Want to know which layer tests what

**Contents**:

- Layer 1: Unit tests of fakes (verify test infrastructure)
- Layer 2: Integration tests with mocking (code coverage)
- Layer 3: Business logic over fakes (majority of tests)
- Layer 4: E2E integration tests (smoke tests)
- Decision tree: where should my test go?
- Test distribution examples

### 📖 `python-specific.md`

**Read when**:

- Working with pytest fixtures
- Need Python mocking patterns
- Testing Flask/FastAPI/Django applications
- Understanding Python testing tools
- Need Python-specific commands

**Contents**:

- pytest fixtures and parametrization
- Mocking with unittest.mock and pytest-mock
- Testing web frameworks (Flask, FastAPI, Django)
- Python testing commands
- Type hints in tests
- Python packaging for test utilities

### 📖 `workflows.md`

**Read when**:

- Adding a new feature (step-by-step)
- Fixing a bug (step-by-step)
- Adding an adapter method (complete checklist)
- Changing an interface (what to update)
- Managing dry-run features

**Contents**:

- Adding a new feature (TDD workflow)
- Fixing a bug (reproduce → fix → regression test)
- Adding an adapter method (8-step checklist with examples)
- Changing an interface (update all layers)
- Managing dry-run features (wrapping pattern)
- Testing with builder patterns

### 📖 `patterns.md`

**Read when**:

- Implementing constructor injection for fakes
- Adding mutation tracking to fakes
- Using CliRunner for CLI tests
- Building complex test scenarios with builders
- Testing dry-run behavior
- Need code examples of specific patterns

**Contents**:

- Constructor injection (how and why)
- Mutation tracking properties (read-only access)
- Using CliRunner (not subprocess)
- Builder patterns for complex scenarios
- Simulated environment pattern
- Error injection pattern
- Dry-run testing pattern

### 📖 `anti-patterns.md`

**Read when**:

- Unsure if your approach is correct
- Want to avoid common mistakes
- Reviewing code for bad patterns
- Debugging why tests are slow/brittle

**Contents**:

- ❌ Testing speculative features
- ❌ Hardcoded paths in tests (catastrophic)
- ❌ Not updating all layers
- ❌ Using subprocess in unit tests
- ❌ Complex logic in adapter classes
- ❌ Fakes with I/O operations
- ❌ Testing implementation details
- ❌ Incomplete test coverage for adapters

### 📖 `quick-reference.md`

**Read when**:

- Quick lookup for file locations
- Finding example tests to reference
- Looking up common fixtures
- Need command reference
- Want test distribution guidelines

**Contents**:

- Decision tree (where to add test)
- File location map (source + tests)
- Common fixtures (tmp_path, CliRunner, etc.)
- Common test patterns (code snippets)
- Example tests to reference
- Useful commands (pytest, pyright, etc.)
- Quick checklist for adding adapter methods

## Quick Navigation by Task

### I'm adding a new feature

1. **Quick start**: `quick-reference.md` → Decision tree
2. **Step-by-step**: `workflows.md#adding-a-new-feature`
3. **Patterns**: `patterns.md` (CliRunner, builders)
4. **Avoid**: `anti-patterns.md` (speculative tests, hardcoded paths)

### I'm fixing a bug

1. **Step-by-step**: `workflows.md#fixing-a-bug`
2. **Patterns**: `patterns.md#constructor-injection-for-fakes`
3. **Examples**: `quick-reference.md#example-tests-to-reference`

### I'm adding/changing an adapter method

1. **Understanding**: `ops-architecture.md`
2. **Step-by-step**: `workflows.md#adding-an-adapter-method`
3. **Checklist**: `quick-reference.md#quick-checklist-adding-a-new-adapter-method`
4. **Avoid**: `anti-patterns.md#not-updating-all-layers`

### I don't know where my test should go

1. **Decision tree**: `quick-reference.md#decision-tree`
2. **Detailed guide**: `testing-strategy.md`
3. **Examples**: `quick-reference.md#example-tests-to-reference`

### I need to implement a pattern

1. **All patterns**: `patterns.md`
2. **Examples**: `quick-reference.md#common-test-patterns`

### I think I'm doing something wrong

1. **Anti-patterns**: `anti-patterns.md`
2. **Correct approach**: `workflows.md`

## Visual Layer Guide

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 4: E2E Integration Tests (5%)                          │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Real database, filesystem, APIs, actual subprocess        │ │
│ │ Purpose: Smoke tests, catch integration issues           │ │
│ │ When: Sparingly, for critical workflows                  │ │
│ │ Speed: Seconds per test                                   │ │
│ │ Location: tests/e2e/ or tests/integration/               │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 3: Business Logic Tests (80%) ← MOST TESTS HERE       │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ FakeDatabase, FakeApiClient, FakeFileSystem              │ │
│ │ Purpose: Test features and business logic extensively    │ │
│ │ When: For EVERY feature and bug fix                      │ │
│ │ Speed: Milliseconds per test                              │ │
│ │ Location: tests/unit/, tests/services/, tests/commands/  │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 2: Adapter Implementation Tests (15%)                  │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ RealDatabase with mocked connections                     │ │
│ │ Purpose: Code coverage of real implementations           │ │
│ │ When: When adding/changing real implementation           │ │
│ │ Speed: Fast (mocked)                                      │ │
│ │ Location: tests/integration/test_real_*.py               │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 1: Fake Infrastructure Tests                           │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Test FakeDatabase itself                                 │ │
│ │ Purpose: Verify test infrastructure is reliable          │ │
│ │ When: When adding/changing fake implementation           │ │
│ │ Speed: Milliseconds per test                              │ │
│ │ Location: tests/unit/fakes/test_fake_*.py               │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Key Principles

1. **Thin adapter layer**: Wrap external state, push complexity to business logic
2. **Fast tests over fakes**: 80% of tests should use in-memory fakes
3. **Defense in depth**: Fakes → mocked real → business logic → e2e
4. **Test what you're building**: No speculative tests, only active work
5. **Update all layers**: When changing interfaces, update ABC/real/fake/dry-run

## Default Testing Strategy

**When in doubt**:

- Write test over fakes (Layer 3)
- Use `pytest` with fixtures
- Use `tmp_path` fixture (not hardcoded paths)
- Follow examples in `quick-reference.md`

## Summary

**For quick tasks**: Start with `quick-reference.md`

**For understanding**: Start with `testing-strategy.md` or `ops-architecture.md`

**For step-by-step guidance**: Use `workflows.md`

**For implementation details**: Use `patterns.md`

**For validation**: Check `anti-patterns.md`

**For Python specifics**: Check `python-specific.md`
