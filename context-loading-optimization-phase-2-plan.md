# Context Loading Optimization - Phase 2 Plan

## Overview

Phase 1 successfully reduced token consumption from ~17,000 to ~7,000 tokens (60% reduction). This document outlines the remaining optimization phases to achieve further reductions and improve the overall documentation structure.

## Completed Work (Phase 1)

✅ **Phase 1: Quick Wins** (Completed)

- Updated devrun hook matcher to fire only on dev tool mentions
- Wrapped kit registry references to prevent auto-expansion
- Achieved 60% token reduction
- All CI checks pass

## Remaining Phases

### Phase 2: Documentation Restructuring

**Goal**: Split monolithic AGENTS.md (672 lines, 28KB) into focused, modular documents

**Implementation Steps**:

1. **Create modular documentation structure**:

   ```
   docs/agent/
   ├── critical-rules.md      # Only the TOP 8 CRITICAL RULES
   ├── python-standards.md     # Link to dignified-python skill
   ├── testing-patterns.md     # Link to fake-driven-testing skill
   ├── graphite-terminology.md # Stack terminology reference
   └── full-reference.md       # Complete documentation (current AGENTS.md)
   ```

2. **Update AGENTS.md to minimal version**:
   - Keep only critical rules that prevent common mistakes
   - Add clear references to specialized documentation
   - Target: Reduce from 28KB to ~8KB

3. **Create skill-based loading pattern**:
   - Python work → Load dignified-python skill
   - Testing → Load fake-driven-testing skill
   - Graphite → Load gt skill
   - General reference → Load full-reference.md on demand

**Expected Impact**:

- Additional 70% reduction in AGENTS.md size
- Total tokens: ~7,000 → ~3,000

### Phase 3: Lazy Documentation Loading

**Goal**: Implement on-demand documentation loading system

**Implementation Steps**:

1. **Create documentation index**:
   - Build searchable index of documentation topics
   - Map keywords to specific documentation files
   - Store in `.agent/docs-index.json`

2. **Implement smart loading**:
   - Detect user intent from message content
   - Load only relevant documentation sections
   - Cache loaded docs for session

3. **Add documentation commands**:
   - `/docs <topic>` - Load specific documentation
   - `/docs-list` - Show available documentation
   - `/docs-clear` - Clear cached documentation

**Expected Impact**:

- Context-aware documentation loading
- Minimal baseline token usage
- Scale to large documentation sets

### Phase 4: Hook System Optimization

**Goal**: Refine hook system for minimal overhead

**Implementation Steps**:

1. **Consolidate Python hooks**:
   - Merge dignified-python and fake-driven-testing reminders
   - Single hook with conditional logic
   - Reduce duplicate system messages

2. **Implement hook priority system**:
   - Critical hooks (security, data safety)
   - Warning hooks (best practices)
   - Info hooks (suggestions)

3. **Add hook configuration UI**:
   - User preferences for hook verbosity
   - Ability to disable non-critical hooks
   - Per-project hook settings

**Expected Impact**:

- Reduce system reminder accumulation
- Cleaner conversation flow
- User control over verbosity

## Implementation Priority

1. **Phase 2** (High Priority): Documentation restructuring provides immediate benefits with low risk
2. **Phase 3** (Medium Priority): Lazy loading adds complexity but enables scaling
3. **Phase 4** (Low Priority): Hook optimization is nice-to-have refinement

## Success Metrics

- **Token Usage**: Target < 3,000 tokens for initial "Hello"
- **Documentation Access**: All docs remain discoverable
- **User Experience**: No loss of functionality
- **Performance**: No noticeable latency increase

## Risk Mitigation

- **Backup Strategy**: Keep original files as `.backup`
- **Rollback Plan**: Single command to restore original configuration
- **Testing Protocol**: Verify each phase independently
- **Gradual Rollout**: Implement phases sequentially, not in parallel

## Notes

- Phase 1 already achieved 60% reduction (17,000 → 7,000 tokens)
- Each additional phase is independent and can be implemented separately
- Focus on maintaining documentation discoverability while reducing auto-loading
- Preserve all safety-critical reminders and hooks

## Context from Phase 1 Planning

### Key Learnings

- Hook matchers use glob syntax, not regex
- @-references auto-expand immediately with no lazy loading
- Kit registry expands recursively (6 files)
- System reminders accumulate throughout conversation
- Documentation intended for layering but became monolithic

### Technical Constraints

- Settings.json expects glob patterns in matcher field
- No built-in lazy loading for markdown references
- Hook system designed for conditional loading
- Token budget: 200,000 per conversation

### Preserved Patterns

- Devrun agent interception for all dev tools
- Safety reminders for Python/testing patterns
- Kit registry accessibility on-demand
- Complete documentation available when needed

---

_This plan preserves the valuable context discovered during Phase 1 planning and implementation, ensuring future phases build on proven patterns and avoid known pitfalls._
