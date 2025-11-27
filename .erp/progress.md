---
completed_steps: 0
total_steps: 33
---

# Progress Tracking

- [ ] 1. Parse the error JSON to understand what failed
- [ ] 2. Display the error message and details to the user
- [ ] 3. **CRITICAL**: Use Bash to exit with non-zero code to propagate failure:
- [ ] 4. DO NOT continue to next steps
- [ ] 1. Parse the error JSON to understand what failed
- [ ] 2. Examine the error type and command output (stdout/stderr in details)
- [ ] 3. Provide clear, helpful guidance based on the specific situation
- [ ] 4. **CRITICAL**: Use Bash to exit with non-zero code to propagate failure:
- [ ] 5. DO NOT retry automatically - let the user decide how to proceed
- [ ] 1. **Add Ensure.gt_authenticated()** in ensure.py
- [ ] 2. **Add auth check to pre-analysis** in submit_branch.py
- [ ] 3. **Update agent prompt** in gt-branch-submitter.md
- [ ] 4. **Integration test**:
- [ ] 5. **Test normal workflow**:
- [ ] 1. Remove Graphite auth token: `gt auth --token ""`
- [ ] 2. Run `/gt:pr-submit "test"`
- [ ] 3. Verify:
- [ ] 1. Re-authenticate: `gt auth --token YOUR_TOKEN`
- [ ] 2. Run `/gt:pr-submit "test"` on real branch
- [ ] 3. Verify:
- [ ] 1. **Reuses existing patterns**: Ensure class, SystemExit(1), JSON error responses
- [ ] 2. **No architectural changes**: Same agent → Python command → subprocess flow
- [ ] 3. **No new dependencies**: Uses existing subprocess, shutil, click imports
- [ ] 4. **No new error types**: Reuses existing error handling infrastructure
- [ ] 5. **Single new method**: Ensure.gt_authenticated() - 20 lines
- [ ] 6. **Single function call**: One line added to execute_pre_analysis()
- [ ] 7. **Documentation updates**: Clarifies existing error handling instructions
- [ ] 1. **Agent must remember to call exit 1**: Not enforced by code, relies on prompt
- [ ] 2. **Auth check happens in Python, not agent**: Could add to agent prompt
- [ ] 3. **Uses gt user tips for auth check**: Not a dedicated auth status command
- [ ] 1. `/Users/schrockn/code/erk/src/erk/cli/ensure.py` - Add gt_authenticated()
- [ ] 2. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py` - Add auth check call
- [ ] 3. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-branch-submitter.md` - Strengthen error handling instructions
