---
completed_steps: 0
total_steps: 17
---

# Progress Tracking

- [ ] 1. **Early exit check (lines 34-36)**: Rejects immediately if no PR exists
- [ ] 2. **publish=False flag (line 52)**: Prevents Graphite from creating new PRs
- [ ] 3. **Incorrect semantics**: Uses `publish=False` which tells gt submit not to create/publish the PR
- [ ] 1. Let `submit` complete (with create or update)
- [ ] 2. Attempt to fetch PR info (as in `submit_branch.py`)
- [ ] 3. Return success with PR details
- [ ] 1. **Branch without PR**: Create new branch, run update-pr → should create new PR
- [ ] 2. **Branch with PR**: Create changes on existing PR branch, run update-pr → should update PR
- [ ] 3. **With uncommitted changes**: Ensure changes are committed before submit
- [ ] 4. **Restack behavior**: With `restack=False`, only the current branch is affected
- [ ] 1. **Why not just use submit_branch.py code?**
- [ ] 2. **Why remove early exit instead of adding another code path?**
- [ ] 3. **restack=False reasoning**:
- [ ] 1. Remove lines 34-36 (early PR existence check)
- [ ] 2. Change line 52: `publish=False` → `publish=True`
- [ ] 3. Optionally add PR info retrieval with retry (following submit_branch.py pattern)
- [ ] 4. Update documentation if needed to clarify that command creates PRs if needed
