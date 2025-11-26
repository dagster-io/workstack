---
completed_steps: 0
total_steps: 22
---

# Progress Tracking

- [ ] 1. The list command is substantial (~150 lines), similar to `wt/list_cmd.py`
- [ ] 2. Follows established patterns for command groups with complex subcommands
- [ ] 3. Better separation of concerns
- [ ] 4. More scalable for future run-related commands
- [ ] 1. **Group definition** (`run/__init__.py`):
- [ ] 2. **Shared utilities** (`run/shared.py`):
- [ ] 3. **List command** (`run/list_cmd.py`):
- [ ] 4. **Logs command** (`run/logs_cmd.py`):
- [ ] 5. **CLI registration** (`cli.py`):
- [ ] 6. **Help formatter** (`help_formatter.py`):
- [ ] 1. **Create command structure**:
- [ ] 2. **Update registrations**:
- [ ] 3. **Manual verification**:
- [ ] 4. **Create test structure**:
- [ ] 5. **Run tests**:
- [ ] 6. **Clean up**:
- [ ] 7. **Final verification**:
- [ ] 1. `/Users/schrockn/code/erk/src/erk/cli/commands/runs.py` - Source to split
- [ ] 2. `/Users/schrockn/code/erk/src/erk/cli/commands/wt/__init__.py` - Pattern for group
- [ ] 3. `/Users/schrockn/code/erk/src/erk/cli/commands/wt/list_cmd.py` - Pattern for command
- [ ] 4. `/Users/schrockn/code/erk/tests/commands/test_runs.py` - Tests to split
- [ ] 5. `/Users/schrockn/code/erk/src/erk/cli/cli.py` - Registration point
