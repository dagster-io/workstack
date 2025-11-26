---
completed_steps: 0
total_steps: 30
---

# Progress Tracking

- [ ] 1. Create src/erk/cli/commands/plan/shared.py
- [ ] 2. Move _parse_identifier() logic from check_cmd.py, rename to parse_plan_identifier()
- [ ] 3. Add comprehensive docstring and type hints
- [ ] 4. Create tests/unit/commands/plan/test_shared.py with 5+ test cases
- [ ] 5. Run uv run pytest tests/unit/commands/plan/test_shared.py - verify all pass
- [ ] 1. Create src/erk/cli/commands/plan/check_helpers.py
- [ ] 2. Extract four validation functions from check_cmd.py lines 83-118
- [ ] 3. Each function returns (bool, str) tuple for pass/fail and description
- [ ] 4. Create tests/unit/commands/plan/test_check_helpers.py with 12+ test cases
- [ ] 5. Run uv run pytest tests/unit/commands/plan/test_check_helpers.py - verify >90% coverage
- [ ] 1. Update imports in check_cmd.py to include new helpers
- [ ] 2. Replace validation blocks (lines 83-118) with helper function calls
- [ ] 3. Replace _parse_identifier() with shared.parse_plan_identifier()
- [ ] 4. Simplify to ~60 lines focused on CLI concerns
- [ ] 5. Run uv run pytest tests/commands/plan/test_check.py - ALL existing tests must pass unchanged
- [ ] 6. Manually test erk plan check 42 - verify output identical to before
- [ ] 1. Update imports in retry_cmd.py to include shared.parse_plan_identifier
- [ ] 2. Replace lines 40-61 with call to shared parser
- [ ] 3. Run uv run pytest tests/commands/plan/test_retry.py - verify no regressions
- [ ] 4. Manually test erk plan retry 42 - verify behavior unchanged
- [ ] 1. Run full test suite: uv run pytest tests/commands/plan/
- [ ] 2. Run pyright: uv run pyright src/erk/cli/commands/plan/
- [ ] 3. Manual smoke test both commands with various identifiers
- [ ] 4. Verify no import cycles or missing dependencies
- [ ] 1. **Reusability**: Validation logic can be imported by webhooks, background jobs, or other commands
- [ ] 2. **Testability**: Unit tests for helpers are faster and more focused than integration tests
- [ ] 3. **Maintainability**: Clear separation between CLI (formatting, exit codes) and business logic (validation)
- [ ] 4. **DRY principle**: Eliminates identifier parsing duplication
- [ ] 5. **Type safety**: Helper functions can have strict type hints verified by pyright
- [ ] 6. **Future flexibility**: Easy to add new validation checks or modify existing ones
