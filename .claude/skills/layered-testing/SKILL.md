---
name: layered-testing
description: This skill should be used when writing tests, fixing bugs, adding features, or modifying the ops layer. Use when you need guidance on testing architecture, working with fakes, implementing ops interfaces, or understanding the defense-in-depth testing strategy. Essential for maintaining test quality and understanding where different types of tests belong.
---

# Layered Testing Architecture

**Use this skill when**: Writing tests, fixing bugs, adding features, or modifying the ops layer (adapters that wrap external state).

## Overview

This codebase uses a **defense-in-depth testing strategy** with four layers:

```
┌─────────────────────────────────────────┐
│  Layer 4: E2E Integration Tests (5%)   │  ← Smoke tests over real system
├─────────────────────────────────────────┤
│  Layer 3: Business Logic Tests (80%)   │  ← Tests over fakes (fast!)
├─────────────────────────────────────────┤
│  Layer 2: Ops Implementation Tests (15%)│  ← Tests WITH mocking
├─────────────────────────────────────────┤
│  Layer 1: Fake Infrastructure Tests    │  ← Verify test doubles work
└─────────────────────────────────────────┘
```

**Philosophy**: Test business logic extensively over fast in-memory fakes. Use real implementations sparingly for integration validation.

**Naming note**: The "ops layer" (adapters/gateways/providers) refers to thin wrappers around heavyweight external APIs (git, filesystem, GitHub API, etc.). The pattern matters more than the name.

## Quick Decision: What Should I Read?

**Adding a feature or fixing a bug?**
→ Read `quick-reference.md` first, then `workflows.md#adding-a-new-feature`

**Need to understand where to put a test?**
→ Read `testing-strategy.md`

**Adding/changing an ops interface?**
→ Read `ops-architecture.md`, then `workflows.md#adding-an-ops-method`

**Need to implement a specific pattern (CliRunner, builders, etc.)?**
→ Read `patterns.md`

**Not sure if I'm doing it right?**
→ Read `anti-patterns.md`

**Just need a quick lookup?**
→ Read `quick-reference.md`

## When to Read Each Reference Document

### 📖 `ops-architecture.md`

**Read when**:

- Adding or changing ops interfaces
- Understanding the ABC/Real/Fake/DryRun pattern
- Need examples of ops implementations
- Want to understand what ops classes are (and why they're thin)

**Contents**:

- What are ops classes? (naming: ops/adapters/gateways)
- The four implementations (ABC, Real, Fake, DryRun)
- Code examples for each
- When to add/change ops methods
- Design principles (keep ops thin)
- Existing ops interfaces (GitOps, GraphiteOps, GitHubOps)

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

### 📖 `workflows.md`

**Read when**:

- Adding a new feature (step-by-step)
- Fixing a bug (step-by-step)
- Adding an ops method (complete checklist)
- Changing an interface (what to update)
- Managing dry-run features

**Contents**:

- Adding a new feature (TDD workflow)
- Fixing a bug (reproduce → fix → regression test)
- Adding an ops method (8-step checklist with examples)
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
- ❌ Complex logic in ops classes
- ❌ Fakes with I/O operations
- ❌ Testing implementation details
- ❌ Incomplete test coverage for ops

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
- Quick checklist for adding ops methods

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

### I'm adding/changing an ops method

1. **Understanding**: `ops-architecture.md`
2. **Step-by-step**: `workflows.md#adding-an-ops-method`
3. **Checklist**: `quick-reference.md#quick-checklist-adding-a-new-ops-method`
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
│ │ Real git, real filesystem, actual subprocess             │ │
│ │ Purpose: Smoke tests, catch integration issues           │ │
│ │ When: Sparingly, for critical workflows                  │ │
│ │ Speed: Seconds per test                                   │ │
│ │ Location: tests/integration/                             │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 3: Business Logic Tests (80%) ← MOST TESTS HERE       │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ FakeGitOps, FakeGraphiteOps, FakeGitHubOps               │ │
│ │ Purpose: Test features and business logic extensively    │ │
│ │ When: For EVERY feature and bug fix                      │ │
│ │ Speed: Milliseconds per test                              │ │
│ │ Location: tests/commands/, tests/unit/                   │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 2: Ops Implementation Tests (15%)                      │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ RealGitOps with mocked subprocess                        │ │
│ │ Purpose: Code coverage of real implementations           │ │
│ │ When: When adding/changing real implementation           │ │
│ │ Speed: Fast (mocked)                                      │ │
│ │ Location: tests/integration/test_real_*.py               │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Layer 1: Fake Infrastructure Tests                           │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Test FakeGitOps itself                                   │ │
│ │ Purpose: Verify test infrastructure is reliable          │ │
│ │ When: When adding/changing fake implementation           │ │
│ │ Speed: Milliseconds per test                              │ │
│ │ Location: tests/unit/fakes/test_fake_*.py               │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Key Principles

1. **Thin ops layer**: Wrap external state, push complexity to business logic
2. **Fast tests over fakes**: 80% of tests should use in-memory fakes
3. **Defense in depth**: Fakes → mocked real → business logic → e2e
4. **Test what you're building**: No speculative tests, only active work
5. **Update all layers**: When changing interfaces, update ABC/real/fake/dry-run

## Default Testing Strategy

**When in doubt**:

- Write test over fakes (Layer 3)
- Use `CliRunner` (not subprocess)
- Use `tmp_path` fixture (not hardcoded paths)
- Follow examples in `quick-reference.md`

## Summary

**For quick tasks**: Start with `quick-reference.md`

**For understanding**: Start with `testing-strategy.md` or `ops-architecture.md`

**For step-by-step guidance**: Use `workflows.md`

**For implementation details**: Use `patterns.md`

**For validation**: Check `anti-patterns.md`

## Related Documentation

- **Project-wide testing**: `docs/agent/testing.md` - Comprehensive testing guide
- **Project terminology**: `docs/agent/glossary.md`
- **Python standards**: Load `dignified-python` skill
- **Test structure**: `tests/AGENTS.md`
