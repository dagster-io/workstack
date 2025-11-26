---
completed_steps: 0
total_steps: 13
---

# Progress Tracking

- [ ] 1. `parse_github_issue_reference()` - Wraps parse_issue_reference with Ensure semantics
- [ ] 2. `github_api_call[T]()` - Generic wrapper for GitHub API RuntimeError handling
- [ ] 1. `src/erk/cli/parse_issue_reference.py` - Shared identifier parsing (~60 lines)
- [ ] 2. `tests/unit/cli/test_parse_issue_reference.py` - Parsing tests (~60 lines)
- [ ] 1. `src/erk/cli/ensure.py` - Add 2 new methods (~40 lines)
- [ ] 2. `src/erk/cli/commands/plan/check_cmd.py` - Use Ensure (~30 lines removed, ~10 added)
- [ ] 3. `tests/unit/cli/test_ensure.py` - Add tests (~20 lines)
- [ ] 1. **Consistency**: All error handling uses Ensure pattern
- [ ] 2. **Reusability**: Other commands can adopt utilities (close_cmd, retry_cmd)
- [ ] 3. **Type Safety**: `github_api_call[T]` preserves return types
- [ ] 4. **Maintainability**: Single source of truth for identifier parsing
- [ ] 5. **Better UX**: Validates positive issue numbers
- [ ] 6. **Testability**: Utilities independently testable
