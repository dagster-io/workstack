<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# Plan: Reorganize `erk runs` to `erk run list`

## Goal

Reorganize the CLI commands from:
- `erk runs` (shows list by default)
- `erk runs logs [RUN_ID]`

To:
- `erk run list` (explicit list subcommand)
- `erk run logs [RUN_ID]` (unchanged)

## Recommended Approach: Directory Structure

**Rationale**: Use the directory structure pattern (like `wt/` and `stack/`) because:
1. The list command is substantial (~150 lines), similar to `wt/list_cmd.py`
2. Follows established patterns for command groups with complex subcommands
3. Better separation of concerns
4. More scalable for future run-related commands

**Alternative**: Single-file approach (like `completion.py`) would work but is less common for groups with substantial subcommands.

## Implementation Overview

### File Structure Changes

**Create new directory**: `src/erk/cli/commands/run/`
```
run/
├── __init__.py              # Group definition, registers subcommands
├── shared.py                # Shared utilities (extract_issue_number)
├── list_cmd.py              # List workflow runs (~150 lines)
└── logs_cmd.py              # View run logs (~50 lines)
```

**Modify existing files**:
- `src/erk/cli/cli.py` - Update import and registration (2 lines)
- `src/erk/cli/help_formatter.py` - Change `"runs"` to `"run"` (1 line)

**Delete old file**:
- `src/erk/cli/commands/runs.py` (210 lines)

**Create test directory**: `tests/commands/run/`
```
run/
├── __init__.py              # Empty package marker
├── test_shared.py           # Tests for extract_issue_number (~75 lines)
├── test_list.py             # Tests for list command (~470 lines)
└── test_logs.py             # Tests for logs command (~130 lines)
```

**Delete old test file**:
- `tests/commands/test_runs.py` (672 lines)

### Key Code Changes

1. **Group definition** (`run/__init__.py`):
   - Remove `invoke_without_command=True` pattern
   - Simple Click group with explicit subcommand registration
   - Pattern: Follow `wt/__init__.py`

2. **Shared utilities** (`run/shared.py`):
   - Extract `_extract_issue_number()` → `extract_issue_number()`
   - Remove leading underscore (now public API in shared module)

3. **List command** (`run/list_cmd.py`):
   - Extract current default list behavior from `runs.py`
   - Use `@click.pass_obj` to receive `ErkContext` directly
   - Import `extract_issue_number` from `shared.py`

4. **Logs command** (`run/logs_cmd.py`):
   - Extract current `logs` subcommand from `runs.py`
   - Minimal changes: decorator and context handling updates

5. **CLI registration** (`cli.py`):
   - Change import: `from erk.cli.commands.run import run_group`
   - Change registration: `cli.add_command(run_group)`

6. **Help formatter** (`help_formatter.py`):
   - Update command groups list: `"runs"` → `"run"`

### Test Changes

**Structure mapping**:
- `shared.py` → `test_shared.py` (tests for `extract_issue_number`)
- `list_cmd.py` → `test_list.py` (tests for list command)
- `logs_cmd.py` → `test_logs.py` (tests for logs command)

**Key updates**:
- Update imports to new module paths
- Change test invocations from group subcommand to direct command invocation
- Rename test functions for clarity (e.g., `test_runs_cmd_*` → `test_list_runs_*`)

## Implementation Sequence

1. **Create command structure**:
   - Create `src/erk/cli/commands/run/` directory
   - Create `__init__.py`, `shared.py`, `list_cmd.py`, `logs_cmd.py`

2. **Update registrations**:
   - Update `cli.py` imports and registration
   - Update `help_formatter.py` command groups

3. **Manual verification**:
   - Test `erk run --help`
   - Test `erk run list`
   - Test `erk run logs`

4. **Create test structure**:
   - Create `tests/commands/run/` directory
   - Create `__init__.py`, `test_shared.py`, `test_list.py`, `test_logs.py`

5. **Run tests**:
   - Run `uv run pytest tests/commands/run/` to verify
   - Run full test suite

6. **Clean up**:
   - Delete `src/erk/cli/commands/runs.py`
   - Delete `tests/commands/test_runs.py`

7. **Final verification**:
   - Full test suite
   - Manual CLI testing

## Design Decisions

### Command name: `run` (singular) vs `runs` (plural)

**Decision**: Use `run` (singular) to match patterns: `erk wt list`, `erk stack move`

### Structure: Directory vs single file

**Decision**: Directory structure because:
- List command is ~150 lines (substantial)
- Matches `wt` and `stack` patterns
- Better scalability

### Helper organization: `shared.py` vs keeping in `list_cmd.py`

**Decision**: Create `shared.py` for `extract_issue_number()` to:
- Avoid importing from sibling command files (anti-pattern)
- Follow dignified Python: explicit shared modules
- Enable future reuse by other run commands

### Backward compatibility

**Decision**: No backward compatibility (clean break)
- Codebase allows breaking changes
- Simpler implementation
- Document in release notes

## Critical Files to Review

1. `/Users/schrockn/code/erk/src/erk/cli/commands/runs.py` - Source to split
2. `/Users/schrockn/code/erk/src/erk/cli/commands/wt/__init__.py` - Pattern for group
3. `/Users/schrockn/code/erk/src/erk/cli/commands/wt/list_cmd.py` - Pattern for command
4. `/Users/schrockn/code/erk/tests/commands/test_runs.py` - Tests to split
5. `/Users/schrockn/code/erk/src/erk/cli/cli.py` - Registration point

## Success Criteria

- [ ] `erk run --help` shows `list` and `logs` subcommands
- [ ] `erk run list` displays workflow runs table
- [ ] `erk run logs [RUN_ID]` shows logs
- [ ] All tests pass
- [ ] Old `erk runs` command no longer exists
- [ ] Help formatter shows `run` in "Command Groups" section

</details>
<!-- /erk:metadata-block:plan-body -->

---

## Execution Commands

**Submit to Erk Queue:**
```bash
erk submit 1285
```

---

### Local Execution

**Standard mode (interactive):**
```bash
erk implement 1285
```

**Yolo mode (fully automated, skips confirmation):**
```bash
erk implement 1285 --yolo
```

**Dangerous mode (auto-submit PR after implementation):**
```bash
erk implement 1285 --dangerous
```