---
completed_steps: 0
total_steps: 7
---

# Progress Tracking

- [ ] 1. **Enhance data model** to include branch names in PR info
- [ ] 2. **Add Issue→PR→Run traversal** logic to fetch workflow runs
- [ ] 3. **Reorganize columns** to move State next to Plan, replace Action with GitHub run data
- [ ] 4. **Display format**: Compact icon + linkified run ID (e.g., `⏳ #12345`)
- [ ] 1. `packages/erk-shared/src/erk_shared/github/types.py` - Add `head_ref_name` field
- [ ] 2. `src/erk/core/github/real.py` - Fetch branch names in PR queries
- [ ] 3. `src/erk/cli/commands/plan/list_cmd.py` - Main display logic changes
