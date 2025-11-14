# Progress Tracking

- [x] 1. **Update validation function signature**: Add `down` parameter to `_validate_landing_preconditions()` in `src/workstack/cli/commands/land_stack/validation.py`
- [x] 2. **Update function call site**: Pass `down` flag when calling validation in `src/workstack/cli/commands/land_stack/command.py`
- [x] 3. **Fix consolidate suggestion**: Update error message to conditionally include `--down` in `src/workstack/cli/commands/land_stack/validation.py`
- [x] 4. **Fix retry suggestion**: Update retry command to include `--down` in `src/workstack/cli/commands/land_stack/validation.py`
- [x] 5. **Add test for --down error message**: Create test case in `tests/commands/graphite/land_stack/test_worktree_handling.py`
- [x] 6. **Run existing tests**: Execute test suite to ensure no regression
