---
completed_steps: 0
total_steps: 20
---

# Progress Tracking

- [ ] 1. **Error Format**: Keep textual-only markdown format for simplicity - errors detected via grep for `^## Error:` prefix
- [ ] 2. **Enrichment Details Section**: Always included in all successful outputs for consistency and transparency
- [ ] 3. **Validation Approach**: Use basic markdown structure validation (checking required headings) instead of kit CLI to avoid adding complexity and failure modes
- [ ] 1. JSON wraps markdown that gets immediately unwrapped via `jq`
- [ ] 2. `enrichment` metadata fields aren't programmatically used by parent commands
- [ ] 3. Adds bash `jq` parsing complexity and failure modes
- [ ] 4. LLMs parse markdown better than JSON
- [ ] 1. Agent returns markdown directly
- [ ] 2. Parent extracts title from first `#` heading
- [ ] 3. Error detection via `## Error:` prefix (simple text match)
- [ ] 4. Cleaner, more readable output
- [ ] 1. **[Question topic]**: [User's answer and how it was incorporated]
- [ ] 2. **[Question topic]**: [User's answer and how it was incorporated]
- [ ] 1. **Update plan-extractor agent** (`plan-extractor.md`)
- [ ] 2. **Update save-plan command** (`save-plan.md`)
- [ ] 3. **Update save-raw-plan command** (`save-raw-plan.md`)
- [ ] 1. Run `/erk:save-plan` with a plan in conversation
- [ ] 2. Run `/erk:save-raw-plan` with ExitPlanMode in session
- [ ] 3. Test error cases (no plan, invalid session)
- [ ] 4. Verify GitHub issue creation still works
