# Plan: Update Documentation for Plan Terminology Simplification

## Context

This plan documents the remaining documentation updates needed after simplifying "Plan Issue" → "Plan" terminology throughout the codebase. All code changes are complete and tests are passing. Only documentation updates remain.

## Objective

Update all user-facing and developer-facing documentation to reflect the new "plan" terminology instead of "plan issue", ensuring consistency across:

- User guides and examples
- Command documentation
- Architecture documentation
- Agent instructions

## Scope

### Files to Update

Based on the implementation plan, the following documentation files need updates:

1. **README.md**
   - Replace "plan issue" with "plan"
   - Update command examples: `erk plan-issue list` → `erk plan list`
   - Update slash command examples: `/erk:save-plan-issue` → `/erk:save-plan`

2. **docs/agent/planning-workflow.md**
   - Update workflow description to use "plan" terminology
   - Update command names and examples
   - Update any references to plan-issue storage or concepts

3. **docs/agent/enrichment-process.md** (if exists)
   - Update any "plan issue" references to "plan"
   - Ensure consistency with new workflow terminology

4. **docs/github-linked-issues.md** (if exists)
   - Clarify distinction between plans (user-facing) and GitHub issues (implementation detail)
   - Update examples to use new terminology

5. **CLAUDE.md** (project root)
   - Update routing table with new command names:
     - `/erk:save-plan-issue` → `/erk:save-plan`
     - `/erk:create-plan-issue-from-plan-file` → `/erk:create-plan-from-file`
     - `/erk:create-queued-plan` → `/erk:queue-plan`

6. **.agent/kits/erk/registry-entry.md**
   - Update kit documentation to reflect new command names
   - Update any examples or descriptions

7. **AGENTS.md** (if it references plan commands)
   - Update routing table if it mentions plan-issue commands
   - Ensure consistency with new terminology

## Implementation Strategy

### Search and Replace Patterns

Use targeted search patterns to find all instances:

```bash
# Find all markdown files with "plan issue" or "plan-issue"
grep -r "plan.issue" docs/ --include="*.md" -i
grep -r "plan.issue" *.md -i
grep -r "plan.issue" .agent/ --include="*.md" -i

# Check for old command references
grep -r "erk plan-issue" docs/ --include="*.md"
grep -r "/erk:save-plan-issue" docs/ --include="*.md"
grep -r "create-plan-issue" docs/ --include="*.md"
```

### Terminology Mapping

| Old Term                              | New Term                   |
| ------------------------------------- | -------------------------- |
| plan issue                            | plan                       |
| plan-issue                            | plan                       |
| PlanIssue                             | Plan                       |
| plan_issue                            | plan                       |
| erk plan-issue                        | erk plan                   |
| /erk:save-plan-issue                  | /erk:save-plan             |
| /erk:create-plan-issue-from-plan-file | /erk:create-plan-from-file |
| /erk:create-queued-plan               | /erk:queue-plan            |

### Preservation Rules

**DO NOT change:**

- GitHub label names: `erk-plan`, `erk-queue` (implementation details)
- Metadata keys: `erk-plan-issue` (backward compatibility)
- Historical references in changelogs or migration guides

## Validation Checklist

After updating documentation:

- [ ] All command examples use `erk plan` not `erk plan-issue`
- [ ] All slash commands use new names (`/erk:save-plan`, etc.)
- [ ] User-facing messages say "plan" not "plan issue"
- [ ] Documentation is consistent across all files
- [ ] No broken links or references to old command names
- [ ] Architecture docs clarify plans vs GitHub issues (implementation detail)

## Success Criteria

Documentation updates are complete when:

1. No references to "plan issue" remain in user-facing docs (except historical context)
2. All command examples reflect new CLI structure
3. All slash command examples use new names
4. Architecture docs clearly explain the abstraction (plans = user concept, issues = implementation)
5. Routing tables and quick-reference guides are updated

## Notes

- This is a documentation-only change; all code changes are complete
- Tests are passing (41/41)
- GitHub labels and metadata keys remain unchanged for backward compatibility
- Focus on user-facing clarity: "plan" is the concept, GitHub issues are the storage mechanism
