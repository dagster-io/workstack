---
completed_steps: 0
total_steps: 6
---

# Progress Tracking

- [ ] 1. **User-friendly error** - Shows red "Error: " prefix with explanation
- [ ] 2. **Type narrowing** - `wt_info` is guaranteed `WorktreeInfo` (not `WorktreeInfo | None`)
- [ ] 3. **Consistent pattern** - Matches other CLI commands using Ensure
- [ ] 1. Add import: `from erk.cli.ensure import Ensure`
- [ ] 2. Replace lines 26-29 with single `Ensure.not_none()` call
- [ ] 3. Run tests to verify behavior
