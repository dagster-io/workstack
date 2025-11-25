<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# Plan: Add Shell Integration for `erk wt create` and `erk wt goto`

## Problem

When running `erk wt create --from-current-branch` or `erk wt goto`, the commands create/navigate worktrees but don't change the shell's directory to the new worktree. The top-level `erk create` command works correctly with shell integration, but `erk wt create` (the subcommand variant) does not.

## Root Cause Analysis

The shell integration handler (`src/erk/cli/shell_integration/handler.py`) only maps top-level commands. When `erk wt create` is invoked:

1. Shell wrapper calls: `erk __shell wt create --from-current-branch`
2. Handler sees `command_name = "wt"` (not in command map at lines 50-59)
3. Falls through to passthrough mode (line 65)
4. No activation script is generated, no directory change happens

The current command map (lines 50-59):
```python
command_map = {
    "checkout": checkout_cmd,
    "co": checkout_cmd,  # Alias
    "create": create_wt,  # Maps `erk create`, NOT `erk wt create`
    "up": up_cmd,
    "down": down_cmd,
    "goto": goto_wt,
    "consolidate": consolidate_stack,
    "implement": implement,
}
```

Note: The `"create"` key maps to `create_wt` because it's registered as a top-level command. This does NOT handle the `wt` subcommand group.

## Solution

Extend the handler to support subcommand groups like `wt`. When `command_name == "wt"`, inspect the next argument to determine the subcommand and route to the appropriate handler.

### Key Design Decisions

1. **Subcommand mapping (only 'create' and 'goto' for now)**: While the wt group has other subcommands (delete, list, rename, current), only create and goto need shell integration (they change directories). Other subcommands can be added later if needed.

2. **Helper function extraction**: Extract command invocation logic into `_invoke_script_command()` helper to reduce duplication and improve testability. Both the existing command_map logic and the new wt subcommand routing will use this helper.

## Implementation

### File: `src/erk/cli/shell_integration/handler.py`

#### 1. Add subcommand map for `wt` group (after imports)

```python
# Map wt subcommand names to their Click commands
WT_SUBCOMMAND_MAP = {
    "create": create_wt,
    "goto": goto_wt,
}
```

Placement: After existing imports and before the `ShellIntegrationResult` dataclass (around line 26-27).

#### 2. Extract helper function for script command invocation

Create new helper function after the `ShellIntegrationResult` dataclass:

```python
def _invoke_script_command(
    command: click.Command,
    args: tuple[str, ...],
    display_name: str
) -> ShellIntegrationResult:
    """Invoke a command with --script flag and return the result.
    
    This helper centralizes command invocation logic used by both the main
    command_map and subcommand routing (e.g., 'wt' subcommands).
    
    Args:
        command: The Click command to invoke
        args: Arguments to pass to the command (--script will be added)
        display_name: Human-readable name for debug logging and user messages
    
    Returns:
        ShellIntegrationResult with passthrough flag, script path, and exit code
    """
    script_args = list(args) + ["--script"]

    debug_log(f"Handler: Invoking {display_name} with args: {script_args}")

    cleanup_stale_scripts(max_age_seconds=STALE_SCRIPT_MAX_AGE_SECONDS)

    runner = CliRunner()
    result = runner.invoke(
        command,
        script_args,
        obj=create_context(dry_run=False, script=True),
        standalone_mode=False,
    )

    exit_code = int(result.exit_code)

    if exit_code != 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=exit_code)

    if result.stderr:
        user_output(result.stderr, nl=False)

    script_path = result.stdout.strip() if result.stdout else None

    debug_log(f"Handler: Got script_path={script_path}, exit_code={exit_code}")

    if script_path:
        script_exists = Path(script_path).exists()
        debug_log(f"Handler: Script exists? {script_exists}")

    if exit_code == 0 and (script_path is None or not script_path):
        user_output(f"Note: '{display_name}' completed (no directory change needed)")

    return ShellIntegrationResult(passthrough=False, script=script_path, exit_code=exit_code)
```

Placement: After `ShellIntegrationResult` dataclass definition (around line 36-37).

#### 3. Modify `_invoke_hidden_command` to handle `wt` subcommands

Replace the existing function (lines 38-109) with:

```python
def _invoke_hidden_command(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    """Invoke a command with --script flag for shell integration.

    If args contain help flags or explicit --script, passthrough to regular command.
    Otherwise, add --script flag and capture the activation script.
    
    Supports both top-level commands and subcommand groups like 'wt'.
    """
    # Check if help flags, --script, or --dry-run are present - these should pass through
    # Dry-run mode should show output directly, not via shell integration
    if "-h" in args or "--help" in args or "--script" in args or "--dry-run" in args:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Handle 'wt' command group - route to subcommand
    if command_name == "wt" and args:
        subcommand_name = args[0]
        subcommand = WT_SUBCOMMAND_MAP.get(subcommand_name)
        if subcommand is not None:
            # Route to subcommand with remaining args
            return _invoke_script_command(subcommand, args[1:], f"wt {subcommand_name}")
        # Unknown wt subcommand - passthrough
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Map command names to their Click commands
    command_map = {
        "checkout": checkout_cmd,
        "co": checkout_cmd,  # Alias
        "create": create_wt,
        "up": up_cmd,
        "down": down_cmd,
        "goto": goto_wt,
        "consolidate": consolidate_stack,
        "implement": implement,
    }

    command = command_map.get(command_name)
    if command is None:
        if command_name in PASSTHROUGH_COMMANDS:
            return _build_passthrough_script(command_name, args)
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    return _invoke_script_command(command, args, command_name)
```

Key changes:
- Added wt subcommand handling before the command_map lookup
- Replaced inline invocation logic with call to `_invoke_script_command` helper
- Kept all error handling and passthrough behavior intact

## Files to Modify

1. **`src/erk/cli/shell_integration/handler.py`**
   - Add `WT_SUBCOMMAND_MAP` constant
   - Add `_invoke_script_command()` helper function
   - Modify `_invoke_hidden_command()` to use helper and support wt subcommands

2. **`tests/unit/shell_integration/test_handler.py`** (new file)
   - Create unit tests for wt subcommand routing
   - Verify 'wt create' generates activation script
   - Verify 'wt goto' generates activation script
   - Verify unknown wt subcommands pass through
   - Verify helper function handles errors correctly

## Testing Strategy

Add tests in `tests/unit/shell_integration/test_handler.py`:

```python
from unittest.mock import Mock, patch
from click.testing import CliRunner
from erk.cli.shell_integration.handler import _invoke_hidden_command, WT_SUBCOMMAND_MAP

def test_wt_create_routes_to_shell_integration() -> None:
    """Verify 'wt create' subcommand is handled by shell integration."""
    # Arrange: Mock the wt create command to return a script path
    # Act: Call _invoke_hidden_command with ("wt", ("create", "--from-current-branch"))
    # Assert: Result should have passthrough=False and script path set (not passthrough)

def test_wt_goto_routes_to_shell_integration() -> None:
    """Verify 'wt goto' subcommand is handled by shell integration."""
    # Arrange: Mock the wt goto command to return a script path
    # Act: Call _invoke_hidden_command with ("wt", ("goto", "some-branch"))
    # Assert: Result should have passthrough=False and script path set

def test_unknown_wt_subcommand_passthrough() -> None:
    """Verify unknown wt subcommands pass through without error."""
    # Arrange: Call with unknown subcommand
    # Act: Call _invoke_hidden_command with ("wt", ("unknown-cmd",))
    # Assert: Result should have passthrough=True

def test_wt_with_no_args_passthrough() -> None:
    """Verify 'wt' with no args passes through gracefully."""
    # Arrange: Call with only "wt"
    # Act: Call _invoke_hidden_command with ("wt", ())
    # Assert: Result should have passthrough=True

def test_invoke_script_command_helper_handles_errors() -> None:
    """Verify _invoke_script_command returns passthrough on command failure."""
    # Arrange: Mock Click command that fails (exit_code != 0)
    # Act: Call _invoke_script_command
    # Assert: Result should have passthrough=True, exit_code > 0
```

## Scope

This change **only affects shell integration routing**. The `wt create` and `wt goto` commands already have full `--script` support implemented, so no changes needed there. The helper function is purely organizational—it doesn't change behavior, just reduces duplication.

## No Changes Required To

- `src/erk/cli/commands/wt/create_cmd.py` - Already supports `--script` flag
- `src/erk/cli/commands/wt/goto_cmd.py` - Already supports `--script` flag
- `src/erk/cli/shell_utils.py` - Navigation script rendering unchanged
- `src/erk/cli/commands/wt/__init__.py` - Command registration unchanged

## Context & Understanding

### Architectural Insights

The shell integration handler uses a **command map dispatch pattern** that only handles top-level commands. The `wt` group is a Click `@click.group()` (see `src/erk/cli/commands/wt/__init__.py` line 13), which creates a composite command with subcommands.

When using Click groups with shell integration, the handler must explicitly handle the group name and then route to subcommands. This is different from normal Click behavior because the shell wrapper intercepts the command before Click's normal group routing occurs.

**Why `create` exists at both levels:**
- `erk create` - Top-level command (direct alias to `create_wt`)
- `erk wt create` - Subcommand via the wt group

Both functions point to the same `create_wt` Click command object. The handler must support both invocation paths.

### Complex Reasoning

**Why extract a helper function?**

Without refactoring, the wt subcommand routing would duplicate the command invocation logic (lines 67-108 of the current handler). This creates maintenance burden: if script handling logic changes, it must be updated in two places.

By extracting `_invoke_script_command()`, both code paths share the same logic. The function signature (`command: click.Command, args: tuple, display_name: str`) is generic enough to support:
- Top-level commands: `_invoke_script_command(checkout_cmd, args, "checkout")`
- Subcommands: `_invoke_script_command(create_wt, args, "wt create")`

**Why check subcommands before the command_map?**

The handler must distinguish:
- `erk wt` → `command_name="wt", args=()` → passthrough (no subcommand)
- `erk wt create` → `command_name="wt", args=("create", ...)` → route to create_wt
- `erk create` → `command_name="create", args=()` → route to create_wt

Checking for `wt` before the command_map ensures we route to the subcommand handler, not treat `wt` as an unknown command.

### Known Pitfalls

1. **Empty args check is critical**: When `command_name="wt"` but `args=()`, we must return passthrough (not try to access `args[0]`). The code guards against this: `if command_name == "wt" and args:`

2. **Display name for user messaging**: The helper function uses `display_name` for the success message (line 107 in current handler). For subcommands, this should be `"wt create"`, not just `"create"`, to match user expectations.

3. **Script path stdout capture**: The current handler captures script path from `result.stdout` after Click 8.2+ stream separation. This behavior is preserved in the helper function and works the same for subcommands.

4. **Passthrough on command failure**: If a subcommand fails (non-zero exit_code), the handler must return `passthrough=True` so the real command runs and shows the error. The helper enforces this.

### Implementation Risks

1. **Test coverage uncertainty**: The new `_invoke_script_command` helper is extracted refactoring logic. Without proper unit tests, regressions could occur if the helper is called with unexpected argument combinations.

2. **Click context injection**: The helper calls `create_context(dry_run=False, script=True)` for every subcommand invocation. This creates a new context each time. Verify that context creation is stateless (no shared mutable state between invocations).

3. **Subcommand discovery at runtime**: The handler requires exact string matching of subcommand names ("create", "goto"). If subcommands are renamed in `wt/__init__.py`, the handler must be updated. No automated validation exists for this mapping.

4. **Incomplete subcommand support**: Only `create` and `goto` are mapped. If future implementations need to support `delete`, `list`, `rename`, or `current` with shell integration, the `WT_SUBCOMMAND_MAP` must be extended.

</details>
<!-- /erk:metadata-block:plan-body -->