---
completed_steps: 0
total_steps: 9
---

# Progress Tracking

- [ ] 1. Derive branch name from original issue title (same logic as workflow)
- [ ] 2. Check if PR exists for that branch: `gh pr view <branch> --json state,number`
- [ ] 3. If PR exists and is OPEN:
- [ ] 4. If PR doesn't exist or already closed, continue silently
- [ ] 1. **`.claude/commands/erk/plan-clone.md`** - Add PR cleanup step
- [ ] 1. Create test issue with erk-plan label and plan content
- [ ] 2. Submit it to create a PR
- [ ] 3. Clone the issue with `/erk:plan-clone`
- [ ] 4. Verify:
