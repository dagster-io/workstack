---
completed_steps: 0
total_steps: 27
---

# Progress Tracking

- [ ] 1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_plan_from_context.py`
- [ ] 2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_enriched_plan_from_context.py`
- [ ] 3. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_erp_from_issue.py`
- [ ] 4. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_issue.py`
- [ ] 5. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_start_comment.py`
- [ ] 6. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/comment_worktree_creation.py`
- [ ] 7. `src/erk/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py`
- [ ] 8. `src/erk/data/kits/erk/kit_cli_commands/erk/post_completion_comment.py`
- [ ] 1. Create `erk_shared/cli.py` with `Ensure` class
- [ ] 2. Update `erk_shared/__init__.py` docstring to document new module
- [ ] 3. Refactor each of the 8 files to use `Ensure.system_exit_boundary`
- [ ] 4. Run pyright and tests
- [ ] 1. **Consistent Error Boundary Pattern**: All 8 commands follow the same error handling pattern for `RuntimeError` exceptions, indicating a systematic refactoring opportunity across the CLI command suite.
- [ ] 2. **Namespace Design Choice**: Using a static class `Ensure` as a namespace (rather than module-level functions or a single function) maintains consistency with other utility patterns in the codebase and provides clear semantic intent through the class name.
- [ ] 3. **Context Manager Justification**: Using `@contextmanager` decorator reduces boilerplate compared to custom `__enter__`/`__exit__` implementations while maintaining readability and testability. The context manager pattern allows for minimal indentation changes in refactored code.
- [ ] 4. **Shared Package Location**: Placing this utility in `erk_shared` rather than `dot-agent-kit` or `erk` directly ensures it's accessible to all CLI commands regardless of which package they're defined in (both dot-agent-kit and erk packages need this functionality).
- [ ] 1. **Click Integration Pattern**: The utility integrates with Click's `click.echo()` and stderr redirection, which is the standard in all CLI commands. Error output must always use `err=True` to ensure error messages go to stderr, not stdout (important for command output parsing).
- [ ] 2. **Exit Code Convention**: The convention to use `SystemExit(1)` for all runtime errors is consistent across all commands and matches standard Unix conventions. This allows calling code to distinguish between success (0) and failure (1).
- [ ] 3. **Error Message Format**: All commands follow the pattern `f"Error: {message}: {e}"` which provides both a high-level message (describing what failed) and the underlying exception details. This format is preserved in the context manager to ensure consistency.
- [ ] 4. **Exception Chaining**: Using `raise SystemExit(1) from e` maintains the exception chain for debugging while transforming the exception type for CLI exit codes. This is important for stack trace preservation.
- [ ] 1. **Mixed Error Handling Patterns**: Not all commands in the target list use identical error handling. For example, `post_progress_comment.py` and `post_completion_comment.py` use different error handling (they return JSON errors instead of stderr messages and use `SystemExit(0)` instead of `SystemExit(1)` in some paths). The refactoring should only apply to commands using the standard RuntimeError -> SystemExit(1) pattern, not to commands with special error handling requirements.
- [ ] 2. **Context Manager Nesting**: Some commands wrap multiple operations. Ensure that nested context managers don't mask earlier exceptions (they won't - the first exception to occur will propagate). Test the refactored code to verify error handling behavior is preserved.
- [ ] 1. **Exact File Count**: Located exactly 8 files with the RuntimeError pattern:
- [ ] 2. **File-by-File Error Patterns**:
- [ ] 1. **Selective Application Required**: This refactoring should ONLY apply to the 8 files using the standard RuntimeError -> SystemExit(1) pattern. Commands with different error handling (like graceful JSON errors with SystemExit(0)) should NOT be refactored with this utility, as it would change their semantics.
- [ ] 2. **Testing Scope**: All 8 commands should have tests that verify:
- [ ] 3. **Documentation Update**: The __init__.py docstring needs to be updated to include the new `cli` module, listing the `Ensure` class and its `system_exit_boundary` context manager.
