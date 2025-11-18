---
enriched_by_persist_plan: true
---

# Update Documentation for Enriched Plan Detection

## Objective

Update all relevant documentation to describe the new enriched plan detection feature in `erk status`. Create a separate developer-only document for the status line implementation. Remove all status line references from user-facing documentation.

## Context & Understanding

### Raw Discoveries Log

- Discovered: Only ONE status line reference exists in user-facing docs (persist-plan.md line 1152)
- Found: 8 documentation files need updates based on comprehensive search
- Learned: Status line implementation lives in separate repository at `/Users/schrockn/code/schrockn-claude/statusline.py`
- Confirmed: Enriched plans use `enriched_by_persist_plan: true` YAML front matter marker
- Verified: Both `.plan/` folder and enriched plan indicators can coexist in `erk status`
- Noted: Display format is `Plan: 🟡 3/10  🆕 feature-plan.md` for both types
- Found: No existing developer documentation for status line implementation

### Architectural Insights

- Two separate display systems: `erk status` (terminal command) and status line (Claude Code UI)
- Status line is maintained in separate repository (schrockn-claude) from erk
- Detection logic is similar but implemented separately in each system
- User-facing documentation should only mention `erk status`, not status line
- Developer documentation needed to document status line for maintainer reference

### Domain Logic & Business Rules

- User-facing docs must NOT mention status line (per user requirement)
- Status line documentation belongs in single developer-only document
- All user-facing examples should show `erk status` output only
- Enriched plans are plans created via `/erk:persist-plan` with front matter marker
- Status indicator format: `🆕 filename` for enriched plans

### Planning Artifacts

**Files Examined:**

- Searched all documentation in README.md, docs/, packages/dot-agent-kit/, .claude/skills/
- Found 8 files requiring updates (listed in implementation steps)
- Found single status line reference in persist-plan.md:1152

**Search Results:**

- User-facing documentation: 1 status line reference to remove
- Implementation files: 3 (should remain as-is, developer-facing)
- Documentation files identified: 8 (listed in High/Medium/Lower priority categories)

## Implementation Steps

### Phase 1: High-Priority User-Facing Documentation

**1. Update README.md**

- File: `README.md` (lines 473-523, 632-660)
- Action: Add enriched plan detection documentation
- Updates:
  - AI-Augmented Planning Workflow section (lines 473-523): Add note that enriched plans display with `🆕 filename` indicator in `erk status`
  - Progress Tracking System section (lines 632-660): Document the enriched plan indicator alongside existing `.plan/` progress indicators
  - Add example: `Plan: 🟡 3/10  🆕 feature-plan.md` (both indicators)
- Success: README documents both `.plan/` and enriched plan indicators
- On failure: Check that examples only show `erk status` output

Related Context:

- Only mention `erk status`, NOT status line (see Domain Logic & Business Rules)
- Show coexistence of both indicator types (see Architectural Insights)

**2. Update /erk:persist-plan command docs**

- File: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/persist-plan.md` (line 1152)
- Action: Remove status line reference, document erk status only
- Current text: "This marker enables detection of enriched plans for status display in both `erk status` and Claude Code status line."
- Updated text: "This marker enables detection of enriched plans for display in `erk status`."
- Success: Status line reference removed, only mentions erk status
- On failure: Verify line 1152 was the only status line mention

Related Context:

- This is the ONLY user-facing status line reference to remove (see Raw Discoveries Log)
- Front matter marker enables detection in erk status (see Domain Logic & Business Rules)

**3. Update Erk Skill Reference**

- File: `.claude/skills/erk/references/erk.md` (lines 470-483, 641-663)
- Action: Add enriched plan indicator documentation
- Updates:
  - Status output section (lines 470-483): Add enriched plan indicator to list of `erk status` elements
  - Plan-Based Development pattern (lines 641-663): Show enriched plan indicator in workflow example
- Success: Skill reference documents enriched plan detection in erk status
- On failure: Verify only erk status mentioned, not status line

Related Context:

- Comprehensive guide for AI assistants (see Planning Artifacts)
- Must maintain consistency with README examples (see Domain Logic & Business Rules)

### Phase 2: Workflow Documentation

**4. Update /erk:implement-plan command docs**

- File: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/implement-plan.md`
- Action: Add brief note about enriched plan indicator
- Update: Add note that enriched plans (from persist-plan) show special indicator in `erk status`
- Success: Command docs mention enriched plan display
- On failure: Verify only mentions erk status

Related Context:

- This command executes plans from .plan/ folders (see Planning Artifacts)
- Keep mention brief, just reference to erk status display

**5. Update /erk:create-planned-wt command docs**

- File: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/create-planned-wt.md`
- Action: Add note about enriched plan indicator
- Update: Note that worktrees created from enriched plans will show indicator in `erk status`
- Success: Command docs mention enriched plan display
- On failure: Verify only mentions erk status

Related Context:

- This command creates worktrees from saved plan files (see Planning Artifacts)
- Plans created via this workflow have enrichment marker (see Domain Logic & Business Rules)

**6. Update Erk Glossary**

- File: `docs/agent/glossary.md` (lines 310-343)
- Action: Enhance Plan Folder definition
- Updates:
  - Distinguish between `.plan/` folders and enriched plan files
  - Add explanation of enrichment marker (`enriched_by_persist_plan: true`)
  - Document status indicators for each type in `erk status`
  - Show example of both indicators together
- Success: Glossary clearly defines both plan types and their indicators
- On failure: Verify terminology is consistent with other docs

Related Context:

- This is the terminology reference (see Planning Artifacts)
- Must establish clear distinction between plan types (see Domain Logic & Business Rules)

### Phase 3: Supplementary Documentation

**7. Update Context Preservation Examples**

- File: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/docs/erk/EXAMPLES.md`
- Action: Add brief mention of enriched plan indicator
- Update: Note that enriched plans (via persist-plan) display with special indicator in `erk status`
- Success: Examples mention enriched plan feature
- On failure: Verify only mentions erk status

Related Context:

- This document explains what makes plans "enriched" (see Planning Artifacts)
- Keep mention brief, focus on context preservation not status display

**8. Update Kit Registry Entry**

- File: `.agent/kits/erk/registry-entry.md`
- Action: Update quick reference
- Update: Mention enriched plan detection capability in `erk status`
- Success: Registry entry references enriched plan feature
- On failure: Verify only mentions erk status

Related Context:

- Quick reference for erk kit (see Planning Artifacts)
- Keep description brief, high-level summary only

### Phase 4: Create Developer-Only Documentation

**9. Create developer documentation for status line**

- File: `docs/developer/status-line.md` (new file)
- Action: Create comprehensive developer reference for status line implementation
- Content structure:
  - Title: "Claude Code Status Line Integration (Developer Reference)"
  - Purpose: Internal documentation for status line implementation details
  - Location: Status line implementation at `/Users/schrockn/code/schrockn-claude/statusline.py`
  - Architecture:
    - `get_enriched_plan(git_root: str) -> str | None` - Detects enriched plans by scanning for `*-plan.md` files with front matter marker
    - `build_enriched_plan_label(filename: str) -> Token` - Formats display as `(🆕 filename)`
    - Integration in statusline assembly (line ~816) - Conditionally includes enriched plan label
  - Display format: `(🆕 filename)` in the status line (different from erk status format)
  - Note: This is separate from `erk status` command and is only for Claude Code UI
  - Note: User-facing documentation should NOT mention this - only document `erk status`
  - Implementation files in statusline.py:
    - Lines 194-254: `get_enriched_plan()` function
    - Lines 699-708: `build_enriched_plan_label()` function
    - Lines 765, 777, 816: Integration points
  - Testing: Status line implementation is in separate repo, test there
- Success: Developer docs provide complete reference for status line
- On failure: Verify file is in docs/developer/ directory (not user-facing location)

Related Context:

- Status line is in separate repository (see Architectural Insights)
- This is the ONLY place status line should be documented (see Domain Logic & Business Rules)
- Detection logic similar to erk status but separate implementation (see Architectural Insights)

## Testing

After all updates:

1. Search all documentation for "status line" or "statusline"
   - Verify: Only found in `docs/developer/status-line.md`
   - Verify: No mentions in README, command docs, glossaries, or skills

2. Review all enriched plan examples
   - Verify: All examples show `erk status` output format
   - Verify: Examples demonstrate both `.plan/` and enriched plan indicators

3. Check terminology consistency
   - Verify: "enriched plans" used consistently
   - Verify: Front matter marker documented consistently
   - Verify: `🆕 filename` format used consistently

4. Validate developer documentation
   - Verify: Status line docs are comprehensive
   - Verify: Location and implementation details are accurate
   - Verify: Clear note that this is developer-only documentation

---

## Progress Tracking

**Current Status:** NOT STARTED

**Last Updated:** 2025-11-18

### Implementation Progress

#### Phase 1: High-Priority User-Facing Documentation

- [ ] Step 1: Update README.md
- [ ] Step 2: Update /erk:persist-plan command docs
- [ ] Step 3: Update Erk Skill Reference

#### Phase 2: Workflow Documentation

- [ ] Step 4: Update /erk:implement-plan command docs
- [ ] Step 5: Update /erk:create-planned-wt command docs
- [ ] Step 6: Update Erk Glossary

#### Phase 3: Supplementary Documentation

- [ ] Step 7: Update Context Preservation Examples
- [ ] Step 8: Update Kit Registry Entry

#### Phase 4: Create Developer-Only Documentation

- [ ] Step 9: Create developer documentation for status line

### Overall Progress

**Steps Completed:** 0 / 9
