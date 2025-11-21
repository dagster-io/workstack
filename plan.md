---
enriched_by_create_enhanced_plan: true
session_id: c7f2030e-5e41-4635-beb2-dc4a45ecc85a
discovery_count: 8
timestamp: 2025-11-21T02:00:00Z
based_on_pr: 685
---

# Phases 7-12: Complete Test Deduplication - Enhanced Implementation Guide

## Executive Summary

Complete the test deduplication initiative by migrating remaining test files (~70 files) to use the comprehensive utility infrastructure built in Phases 1-6. All foundational utilities are production-ready and proven through Phase 5 & 6 implementation (PR #685 submitted).

**Phases 7-11**: Systematic migration of workspace, navigation, graphite, display/sync, and core test modules
**Phase 12**: Documentation consolidation and developer onboarding materials

**Total Remaining Impact**: 1,100-1,550 lines of test boilerplate to eliminate across ~70 files.

---

## Critical Context from Planning

### What We Learned

#### Infrastructure Maturity (Phases 1-6 Complete)

- **All utilities are production-ready**: Phases 1-4 merged, Phase 5 & 6 submitted in PR #685
- **Proven at scale**: Land_stack tests (9 files) successfully demonstrate BranchStackBuilder + build_ops_from_branches()
- **High adoption already**: setup_repo_structure() actively used in test_create.py, build_ops_from_branches() used 22 times
- **No technical blockers**: All infrastructure type-checked, tested, and validated with 1,642 passing tests

#### Current Migration Status by Module

**Workspace Commands** (Phase 7 target):

- test_create.py: 12 remaining repo_dir patterns (was 37, significant reduction)
- test_split.py, test_consolidate.py, test_delete.py: Already clean
- Primary work: Complete WorktreeInfo migration in test_create.py

**Navigation Commands** (Phase 8 target):

- test_up.py: 3 WorktreeInfo instances remaining
- test_down.py: Not fully audited yet
- test_stack_navigation.py: May already be clean from Phase 5-6 work

**Graphite Commands** (Phase 9 target):

- Land_stack tests (9 files): ✅ WELL-MIGRATED using BranchStackBuilder
- All land_stack tests using build_ops_from_branches() consistently
- Other graphite commands: Status unknown, likely minimal work

**Display & Sync Commands** (Phase 10 target):

- test_sync.py: 13 WorktreeInfo remaining (down from 37, 65% migrated)
- Display tests: Not audited yet

**Core & Polish** (Phase 11 target):

- ~27 core test files not yet audited
- Full grep scan needed to identify remaining patterns

#### Key Utilities Available for Migration

From Phases 1-6 (all production-ready):

1. **Context Builders** (Phase 1): build_workspace_test_context(), build_graphite_test_context()
2. **CLI Assertion Helpers** (Phase 2): assert_cli_success(), assert_cli_error()
3. **setup_repo_structure()** (Phase 3): Single-line repo directory setup
4. **Smart build_context()** (Phase 4): Automatic FakeGit configuration via current_branch parameter
5. **build_worktrees()** (Phase 5): One-line WorktreeInfo list construction
6. **BranchStackBuilder** (Phase 6): Fluent API for BranchMetadata stacks

### What Didn't Work

#### Research Phase Findings

No failures during research - all utilities confirmed working and in use.

### Raw Discoveries Log

- **Discovered**: Phases 5-6 utilities already implemented and proven (not just planned)
- **Confirmed**: BranchStackBuilder exists in builders.py with full implementation
- **Observed**: Land_stack tests demonstrate successful pattern adoption (20+ uses of build_ops_from_branches)
- **Measured**: test_sync.py has 13 WorktreeInfo remaining (down from 37 originally)
- **Found**: test_create.py partially migrated with 12 repo_dir patterns remaining
- **Validated**: All infrastructure is type-checked and test-validated
- **Learned**: libcst-refactor agent is ideal tool for systematic Python refactoring
- **Confirmed**: Sequential phase execution reduces merge conflict risk

---

## Implementation Plan

### Objective

Complete Phases 7-12 of the test deduplication initiative by systematically migrating all remaining test files to use modern utility patterns, then consolidating documentation to ensure long-term adoption.

### Implementation Steps

#### Phase 7: Workspace Commands Migration

**1. Audit test_create.py for remaining patterns**

File: `tests/commands/workspace/test_create.py` (1,616 lines)

[CRITICAL: Load dignified-python and fake-driven-testing skills before editing]

Tasks:

- Count exact WorktreeInfo instances needing migration
- Identify remaining manual FakeGit constructions that could use smart defaults
- Review 12 repo_dir patterns (may already be using setup_repo_structure())
- Plan migration approach (manual vs libcst-refactor agent)

Success Criteria:

- Complete inventory of remaining duplication patterns
- Migration strategy determined

Related Context:

- test_create.py already uses setup_repo_structure() (line 20)
- test_create.py already uses build_context() (line 31)
- Focus on WorktreeInfo and FakeGit patterns

**2. Migrate test_create.py to modern patterns**

Using libcst-refactor agent or manual edits:

- Replace manual WorktreeInfo lists with `env.build_worktrees()`
- Replace verbose FakeGit construction with `env.build_context(current_branch=...)`
- Verify all 12 repo_dir patterns use setup_repo_structure()
- Update assertions to use assert_cli_success() / assert_cli_error()

Success Criteria:

- Zero manual WorktreeInfo constructions remain
- All FakeGit uses smart defaults where applicable
- All tests pass (`uv run pytest tests/commands/workspace/test_create.py`)

Related Context:

- Pattern: WorktreeInfo lists 10-15 lines → 1 line with build_worktrees()
- Pattern: FakeGit(git_common_dirs=..., default_branches=...) → build_context(current_branch=...)

**3. Audit and migrate test_split.py, test_consolidate.py, test_delete.py**

For each file:

- Verify already using modern patterns
- Check for any remaining WorktreeInfo instances
- Check for any remaining manual FakeGit patterns
- Apply fixes if needed

Success Criteria:

- All 3 files confirmed clean or migrated
- Consistent pattern usage across all workspace tests

**4. Run /fast-ci to validate Phase 7**

Execute `/fast-ci` command to verify all changes

Success Criteria:

- All unit tests pass
- No regressions introduced
- Estimated 300-400 lines eliminated

Related Context:

- Use devrun agent for test execution (project requirement)

---

#### Phase 8: Navigation Commands Migration

**1. Complete test_up.py migration**

File: `tests/commands/navigation/test_up.py`

- Replace 3 remaining WorktreeInfo instances with `env.build_worktrees()`
- Check for FakeGit smart defaults opportunities
- Verify setup_repo_structure() usage

Success Criteria:

- Zero manual WorktreeInfo constructions remain
- All tests pass

**2. Audit and migrate test_down.py**

Similar approach to test_up.py:

- Full WorktreeInfo audit
- Apply build_worktrees() pattern
- Smart defaults for FakeGit

Success Criteria:

- Consistent with test_up.py migration
- All tests pass

**3. Verify test_stack_navigation.py migration status**

[CRITICAL: May already be complete from Phase 5-6 work]

Check if Phase 5-6 already migrated this file:

- Audit for remaining manual WorktreeInfo
- Audit for remaining BranchMetadata (should use BranchStackBuilder)
- Apply any remaining fixes

Success Criteria:

- File uses modern patterns consistently
- All tests pass

**4. Migrate test_checkout.py and related files**

Apply same migration approach to remaining navigation tests

Success Criteria:

- All 5 navigation test files modernized
- Consistent pattern usage

**5. Run /fast-ci to validate Phase 8**

Success Criteria:

- All unit tests pass
- Estimated 200-300 lines eliminated

---

#### Phase 9: Graphite Commands Polish & Consolidation

[CRITICAL: Land_stack tests already well-migrated, focus on consistency]

**1. Verify land_stack test consistency**

Files: 9 land_stack test files in `tests/commands/land_stack/`

Tasks:

- Verify all 9 files use BranchStackBuilder consistently
- Verify all use build_ops_from_branches() where applicable
- Check for any remaining manual patterns
- Ensure consistent import statements

Success Criteria:

- All land_stack tests follow identical patterns
- No manual BranchMetadata construction remains

Related Context:

- build_ops_from_branches() has 22 uses, 20 in land_stack tests
- BranchStackBuilder already in active use
- These files are reference implementations for other phases

**2. Audit and migrate other Graphite command tests**

Files: ~6 additional graphite test files (not in land_stack/)

- Full audit for duplication patterns
- Apply Phases 1-6 utilities as applicable
- Ensure consistency with land_stack tests

Success Criteria:

- All graphite tests modernized
- Consistent patterns across all graphite module

**3. Run /fast-ci to validate Phase 9**

Success Criteria:

- All tests pass
- Estimated 250-350 lines eliminated

---

#### Phase 10: Display & Sync Commands Migration

**1. Complete test_sync.py WorktreeInfo migration**

File: `tests/commands/sync/test_sync.py`

[CRITICAL: 13 WorktreeInfo instances remaining (down from 37)]

Tasks:

- Identify all 13 remaining WorktreeInfo instances
- Replace with `env.build_worktrees()` pattern
- Check for FakeGit smart defaults opportunities
- Verify setup_repo_structure() usage

Success Criteria:

- Zero manual WorktreeInfo constructions remain
- All tests pass
- Estimated 65-100 lines eliminated from this file alone

Related Context:

- File has already been partially migrated (65% complete)
- Follow patterns from test_stack_navigation.py migration

**2. Audit and migrate display test files**

Files: ~4 display test files

- display/list/test_basic.py
- display/list/test_pr_info.py
- display/list/test_trunk_detection.py
- display/test_current.py

Tasks:

- Full duplication pattern audit
- Apply applicable utilities
- Focus on output assertion patterns (assert_cli_output_contains)

Success Criteria:

- All display tests modernized
- Consistent patterns across display module

**3. Run /fast-ci to validate Phase 10**

Success Criteria:

- All tests pass
- Estimated 200-300 lines eliminated

---

#### Phase 11: Core, Config & Polish

**1. Comprehensive duplication audit**

[CRITICAL: Use Explore or Plan agent for systematic search across ~27 core test files]

Search patterns:

- `grep -r "repo_dir = env.erk_root" tests/core/` - Find remaining repo_dir patterns
- `grep -r "WorktreeInfo\(" tests/core/` - Find remaining manual WorktreeInfo
- `grep -r "BranchMetadata\.trunk\(" tests/core/` - Find remaining manual BranchMetadata
- `grep -r "assert result\.exit_code ==" tests/` - Find remaining old assertions

Create comprehensive list:

- File path
- Pattern type
- Instance count
- Migration priority

Success Criteria:

- Complete inventory of all remaining patterns
- Prioritized migration list

Related Context:

- Use Task tool with Explore agent for efficient search
- Focus on core/ and any files not covered in Phases 7-10

**2. Systematic migration of identified patterns**

For each file in priority order:

- Apply appropriate Phase 1-6 utility
- Run tests after each file migration
- Track progress with TodoWrite

Success Criteria:

- All identified patterns migrated
- File-by-file validation

**3. Final consistency sweep**

Tasks:

- Verify all test files use modern patterns
- Check imports are correct
- Look for opportunities to extract common scenarios
- Ensure no old patterns remain

Success Criteria:

- Zero grep matches for old patterns
- 100% modern pattern adoption

**4. Run /all-ci for comprehensive validation**

[CRITICAL: Include integration tests for final validation]

Success Criteria:

- All unit tests pass
- All integration tests pass
- No regressions introduced
- Estimated 150-200 lines eliminated

Related Context:

- Use devrun agent for execution
- /all-ci runs full test suite including integration tests

---

#### Phase 12: Documentation & Examples

**1. Create tests/test_utils/README.md**

[CRITICAL: This is a NEW file, not editing existing]

Content structure:

- Quick Start guide with minimal example
- Available Utilities catalog with descriptions
- Context Builders section (build_workspace_test_context, etc.)
- Environment Helpers section (setup_repo_structure, build_worktrees, etc.)
- Builders section (BranchStackBuilder, WorktreeScenario, etc.)
- Assertion Helpers section (assert_cli_success, assert_cli_error, etc.)
- Common Patterns with before/after examples
- Migration Guide for updating old tests

Success Criteria:

- Comprehensive reference for all test utilities
- Clear examples for each utility
- Easy to navigate and search

Related Context:

- Use land_stack tests as reference implementations
- Include examples from Phases 5-6 migration

**2. Update AGENTS.md with modern test patterns**

Add section after existing testing content:

```markdown
## Modern Test Patterns (Phases 1-12)

### Pattern: Workspace Command Test

[Before/after example using utilities]

### Pattern: Navigation Test with Stacks

[Before/after example using BranchStackBuilder]

### Pattern: Graphite Test

[Before/after example using build_ops_from_branches]
```

Success Criteria:

- Examples added to AGENTS.md
- Patterns visible to AI assistants
- Clear before/after comparisons

**3. Update docs/agent/testing.md**

Add new sections:

- "Modern Test Utilities" - Overview with links to README
- "Migration Guide" - How to update old tests
- "Anti-Patterns" - What to avoid (manual construction patterns)

Success Criteria:

- Documentation reflects current state
- Clear guidance for new test development

**4. Create reference implementation examples**

[CRITICAL: Only if valuable - don't create unnecessary files]

Consider creating `tests/test_utils/examples/` with:

- modern_workspace_test.py
- modern_navigation_test.py
- modern_graphite_test.py

Success Criteria:

- Working examples demonstrating all utilities
- Developers can copy-paste as starting point

**5. Run /fast-ci to validate documentation**

Verify:

- All documentation renders correctly
- No broken links
- Examples are accurate

Success Criteria:

- Documentation CI checks pass (prettier, md-check)

---

### Testing

**Per-Phase Testing:**

- Phase 7-11: Run `/fast-ci` after each phase completes
- Phase 11: Run `/all-ci` for comprehensive validation
- Phase 12: Run prettier and md-check validation

**Regression Prevention:**

- Each file migration is independent - test immediately after changes
- Use devrun agent for all pytest/pyright/ruff execution
- Keep changes focused - don't mix refactoring with other improvements

---

## Progress Tracking

**Current Status:** Planning complete, ready for Phase 7 implementation

**Last Updated:** 2025-11-20

### Phase 7: Workspace Commands Migration

- [ ] Audit test_create.py for remaining patterns
- [ ] Migrate test_create.py to modern patterns
- [ ] Audit and migrate test_split.py, test_consolidate.py, test_delete.py
- [ ] Run /fast-ci to validate Phase 7

### Phase 8: Navigation Commands Migration

- [ ] Complete test_up.py migration (3 WorktreeInfo remaining)
- [ ] Audit and migrate test_down.py
- [ ] Verify test_stack_navigation.py migration status
- [ ] Migrate test_checkout.py and related files
- [ ] Run /fast-ci to validate Phase 8

### Phase 9: Graphite Commands Polish

- [ ] Verify land_stack test consistency (9 files)
- [ ] Audit and migrate other Graphite command tests
- [ ] Run /fast-ci to validate Phase 9

### Phase 10: Display & Sync Commands Migration

- [ ] Complete test_sync.py WorktreeInfo migration (13 remaining)
- [ ] Audit and migrate display test files
- [ ] Run /fast-ci to validate Phase 10

### Phase 11: Core, Config & Polish

- [ ] Comprehensive duplication audit (grep scan)
- [ ] Systematic migration of identified patterns
- [ ] Final consistency sweep
- [ ] Run /all-ci for comprehensive validation

### Phase 12: Documentation & Examples

- [ ] Create tests/test_utils/README.md
- [ ] Update AGENTS.md with modern test patterns
- [ ] Update docs/agent/testing.md
- [ ] Create reference implementation examples (if valuable)
- [ ] Run /fast-ci to validate documentation

### Overall Progress

**Phases Completed:** 6 / 12 (50%)
**Foundation Complete:** ✅ Phases 1-6
**Migration Pending:** Phases 7-11
**Documentation Pending:** Phase 12

---

## Appendices

### A. Infrastructure Verification

**Available Utilities** (all confirmed working):

From `tests/test_utils/env_helpers.py`:

- `setup_repo_structure()` - Lines 321 (ErkInMemEnv), 731 (ErkIsolatedFsEnv)
- `build_worktrees()` - Lines 183 (ErkInMemEnv), 731 (ErkIsolatedFsEnv)
- `build_context()` - Enhanced with smart defaults
- `build_ops_from_branches()` - 22 uses in codebase

From `tests/test_utils/builders.py`:

- `BranchStackBuilder` - Line 420, full implementation with add_linear_stack(), add_branch(), etc.

From `tests/test_utils/cli_helpers.py`:

- `assert_cli_success()`, `assert_cli_error()`, `assert_cli_output_contains()`

### B. Migration Reference Patterns

**Pattern 1: WorktreeInfo → build_worktrees()**

Before (10-15 lines):

```python
worktrees={
    env.cwd: [
        WorktreeInfo(path=env.cwd, branch="main", is_root=True),
        WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
        WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
    ]
}
```

After (1 line):

```python
worktrees=env.build_worktrees("main", ["feat-1", "feat-2"], repo_dir=repo_dir)
```

**Pattern 2: BranchMetadata → BranchStackBuilder**

Before (6-10 lines):

```python
branches={
    "main": BranchMetadata.trunk("main", children=["feat-1"]),
    "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
    "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
}
```

After (1 line):

```python
branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build()
```

**Pattern 3: FakeGit → Smart Defaults**

Before (5-8 lines):

```python
git_ops = FakeGit(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
    current_branches={env.cwd: "feature"},
)
test_ctx = env.build_context(git=git_ops)
```

After (1 line):

```python
test_ctx = env.build_context(current_branch="feature")
```

### C. File Counts and Priorities

**Phase 7** (4 files):

- test_create.py - HIGHEST PRIORITY (1,616 lines, most duplication)
- test_split.py, test_consolidate.py, test_delete.py - VERIFY CLEAN

**Phase 8** (5 files):

- test_up.py - 3 WorktreeInfo to migrate
- test_down.py, test_stack_navigation.py - AUDIT STATUS
- test_checkout.py, test_checkout_messages.py - FULL MIGRATION

**Phase 9** (~15 files):

- 9 land_stack files - VERIFY CONSISTENCY
- ~6 other graphite files - FULL MIGRATION

**Phase 10** (~5-10 files):

- test_sync.py - 13 WorktreeInfo to migrate
- 4 display files - FULL AUDIT + MIGRATION

**Phase 11** (~27+ files):

- All core/ test files - FULL AUDIT
- Stragglers from Phases 7-10 - POLISH

### D. Success Metrics

**Quantitative Targets:**

- Lines removed (Phases 7-12): 1,100-1,550
- Combined with Phases 1-6: 1,600-2,050 total
- Pattern elimination: 100% (zero old patterns remain)
- Test coverage: Maintained at 100% passing

**Qualitative Goals:**

- Test readability significantly improved
- New tests easier to write (lower cognitive load)
- Patterns self-documenting through helper names
- Consistent patterns across entire test suite

### E. Execution Strategy

**Recommended Approach:** Sequential execution (Phase 7 → 8 → 9 → 10 → 11 → 12)

**Why Sequential:**

- Each phase builds on previous (reference implementation)
- Reduces merge conflict risk (different modules)
- Earlier phases reveal patterns for later phases
- Phase 12 consolidates all learnings from 7-11

**Dependencies:**

- All phases require Phase 5 merged (build_worktrees available)
- All phases require Phase 6 merged (BranchStackBuilder available)
- Phase 12 requires Phases 7-11 complete (all examples available)

**Parallel Work Alternative:**
If time-critical, Phases 8+9+10 could run concurrently after Phase 7 completes, but sequential is safer.

### F. Key Discoveries Not to Lose

1. **Infrastructure is production-ready** - Phases 1-6 all working, tested, type-checked, no blockers

2. **libcst-refactor agent is ideal tool** - Use for systematic Python transformations (proven in Phase 6)

3. **Land_stack tests are reference implementation** - 9 files successfully demonstrate all new patterns

4. **Partial migration already exists** - test_create.py, test_sync.py show prior migration work

5. **Smart defaults work well** - env.build_context(current_branch=...) eliminates 5-8 lines per test

6. **BranchStackBuilder simplifies significantly** - 10 lines of BranchMetadata → 1 line builder call

7. **Sequential execution is safer** - Each phase provides reference for next, reduces conflicts

8. **Documentation is critical** - tests/test_utils/README.md will drive long-term adoption

### G. Risk Mitigation

**Risk: Merge conflicts between sequential phases**

- **Mitigation**: Phases touch different modules/directories (low overlap)
- **Recovery**: Rebase frequently, communicate timing

**Risk: Missing patterns in Phase 11 audit**

- **Mitigation**: Use automated grep scans + Explore agent for comprehensive search
- **Recovery**: Track all pattern types with checklist, verify zero matches at end

**Risk: Documentation not adopted after Phase 12**

- **Mitigation**: Put examples in AGENTS.md (AI-visible), create tests/test_utils/README.md
- **Recovery**: Monitor new test PRs, provide feedback on pattern usage
