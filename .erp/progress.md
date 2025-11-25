---
completed_steps: 0
total_steps: 16
---

# Progress Tracking

- [ ] 1. Shell wrapper calls: `erk __shell wt create --from-current-branch`
- [ ] 2. Handler sees `command_name = "wt"` (not in command map at lines 50-59)
- [ ] 3. Falls through to passthrough mode (line 65)
- [ ] 4. No activation script is generated, no directory change happens
- [ ] 1. **Subcommand mapping (only 'create' and 'goto' for now)**: While the wt group has other subcommands (delete, list, rename, current), only create and goto need shell integration (they change directories). Other subcommands can be added later if needed.
- [ ] 2. **Helper function extraction**: Extract command invocation logic into `_invoke_script_command()` helper to reduce duplication and improve testability. Both the existing command_map logic and the new wt subcommand routing will use this helper.
- [ ] 1. **`src/erk/cli/shell_integration/handler.py`**
- [ ] 2. **`tests/unit/shell_integration/test_handler.py`** (new file)
- [ ] 1. **Empty args check is critical**: When `command_name="wt"` but `args=()`, we must return passthrough (not try to access `args[0]`). The code guards against this: `if command_name == "wt" and args:`
- [ ] 2. **Display name for user messaging**: The helper function uses `display_name` for the success message (line 107 in current handler). For subcommands, this should be `"wt create"`, not just `"create"`, to match user expectations.
- [ ] 3. **Script path stdout capture**: The current handler captures script path from `result.stdout` after Click 8.2+ stream separation. This behavior is preserved in the helper function and works the same for subcommands.
- [ ] 4. **Passthrough on command failure**: If a subcommand fails (non-zero exit_code), the handler must return `passthrough=True` so the real command runs and shows the error. The helper enforces this.
- [ ] 1. **Test coverage uncertainty**: The new `_invoke_script_command` helper is extracted refactoring logic. Without proper unit tests, regressions could occur if the helper is called with unexpected argument combinations.
- [ ] 2. **Click context injection**: The helper calls `create_context(dry_run=False, script=True)` for every subcommand invocation. This creates a new context each time. Verify that context creation is stateless (no shared mutable state between invocations).
- [ ] 3. **Subcommand discovery at runtime**: The handler requires exact string matching of subcommand names ("create", "goto"). If subcommands are renamed in `wt/__init__.py`, the handler must be updated. No automated validation exists for this mapping.
- [ ] 4. **Incomplete subcommand support**: Only `create` and `goto` are mapped. If future implementations need to support `delete`, `list`, `rename`, or `current` with shell integration, the `WT_SUBCOMMAND_MAP` must be extended.
