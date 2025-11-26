---
completed_steps: 0
total_steps: 33
---

# Progress Tracking

- [ ] 1. **Primary**: Refactor uniform try-catch patterns in `create_cmd.py` using domain-specific Ensure methods
- [ ] 2. **Secondary**: Fix kit CLI command function name mismatches causing warnings
- [ ] 1. **Line 61**: OSError reading file
- [ ] 2. **Line 68**: OSError reading stdin
- [ ] 3. **Line 98**: RuntimeError ensuring label exists
- [ ] 4. **Line 128**: RuntimeError creating issue
- [ ] 5. **Line 141**: RuntimeError adding comment (Warning variant)
- [ ] 1. **Warning variant** (create_cmd.py:134-141) - Uses yellow "Warning:" styling, non-fatal
- [ ] 2. **CalledProcessError with special handling** - Has conditional logic based on return code
- [ ] 3. **ClickException** (implement.py:136) - Uses Click's exception system, not SystemExit
- [ ] 4. **from None** (runs.py:209) - Deliberately suppresses exception chain
- [ ] 1. `/Users/schrockn/code/erk/src/erk/cli/ensure.py` - Add 3 new methods
- [ ] 2. `/Users/schrockn/code/erk/tests/unit/cli/test_ensure.py` - Add 3 test classes
- [ ] 3. `/Users/schrockn/code/erk/src/erk/cli/commands/plan/create_cmd.py` - Migrate 4 instances
- [ ] 1. Add 3 new methods to `/Users/schrockn/code/erk/src/erk/cli/ensure.py`
- [ ] 2. Update imports and module docstring
- [ ] 1. Add 3 test classes to `/Users/schrockn/code/erk/tests/unit/cli/test_ensure.py`
- [ ] 2. Run tests: Use devrun agent for `pytest tests/unit/cli/test_ensure.py`
- [ ] 1. Rename `save_plan_from_session` → `plan_save_from_session`
- [ ] 2. Rename `debug_agent` → `agent_debug`
- [ ] 3. Verify warnings disappear
- [ ] 1. Convert 4 try-catch blocks in `create_cmd.py`
- [ ] 2. Keep Warning variant unchanged (line 131-141)
- [ ] 1. Run unit tests via devrun agent
- [ ] 2. Run command tests via devrun agent: `pytest tests/commands/plan/test_create.py`
- [ ] 3. Run pyright via devrun agent on modified files
- [ ] 4. Manual smoke tests for create_cmd.py
- [ ] 5. Verify kit CLI warnings gone
- [ ] 1. `/Users/schrockn/code/erk/src/erk/cli/ensure.py` - Add 3 methods
- [ ] 2. `/Users/schrockn/code/erk/tests/unit/cli/test_ensure.py` - Add 3 test classes
- [ ] 3. `/Users/schrockn/code/erk/src/erk/cli/commands/plan/create_cmd.py` - Migrate 4 blocks
- [ ] 4. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_from_session.py` - Rename function
- [ ] 5. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/agent_debug.py` - Rename function
