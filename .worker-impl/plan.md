# Fix get-closing-text CLI Command Warning + Add Loading Documentation

## Problem

The `get-closing-text` CLI command produces a warning during loading because:

1. The command loader (`group.py:133`) converts command names to function names by replacing hyphens with underscores: `get-closing-text` → `get_closing_text`
2. The CLI file (`get_closing_text.py`) defines the function as `get_closing_text_cmd` (not `get_closing_text`)
3. This was done to avoid a naming collision with the imported canonical function `from erk_shared.impl_folder import get_closing_text`

**Warning message:**
```
Warning: Command 'get-closing-text' in kit 'erk' does not have expected function 'get_closing_text' in module ...
```

## Solution

Two changes:

### 1. Fix the Command

Rename the function back to `get_closing_text` and use an import alias for the canonical function.

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/get_closing_text.py`

Change:
```python
@click.command(name="get-closing-text")
def get_closing_text_cmd() -> None:
    ...
    from erk_shared.impl_folder import get_closing_text
    ...
    closing_text = get_closing_text(impl_dir)
```

To:
```python
@click.command(name="get-closing-text")
def get_closing_text() -> None:
    ...
    from erk_shared.impl_folder import get_closing_text as get_closing_text_impl
    ...
    closing_text = get_closing_text_impl(impl_dir)
```

### 2. Add Documentation Section

Add a new section to `docs/agent/kit-cli-commands.md` at the end documenting the command loading mechanics:

```markdown
## Command Loading and Naming Conventions

Kit CLI commands are loaded lazily by `LazyKitGroup` in `dot_agent_kit/commands/kit_command/group.py`.

### Naming Convention

Command names use **kebab-case**, function names use **snake_case**:

| Command Name (kit.yaml) | Expected Function Name |
|-------------------------|------------------------|
| `get-closing-text`      | `get_closing_text`     |
| `plan-save-to-issue`    | `plan_save_to_issue`   |
| `submit-branch`         | `submit_branch`        |

The loader converts hyphens to underscores automatically (line 133 in `group.py`).

### Handling Import Collisions

When your CLI command function would collide with an imported function name, use an import alias:

**Problem:**
```python
from erk_shared.impl_folder import get_closing_text  # Collision!

@click.command(name="get-closing-text")
def get_closing_text() -> None:  # Same name as import
    closing_text = get_closing_text(impl_dir)  # Which one?
```

**Solution - use import alias:**
```python
from erk_shared.impl_folder import get_closing_text as get_closing_text_impl

@click.command(name="get-closing-text")
def get_closing_text() -> None:
    closing_text = get_closing_text_impl(impl_dir)  # Clear!
```

**DO NOT** rename the function with a `_cmd` suffix - this breaks the loader's name resolution.

### Validation Rules

Commands are validated during loading. Each command must have:

1. **Name**: lowercase letters, numbers, hyphens only (`^[a-z][a-z0-9-]*$`)
2. **Path**: must end with `.py` and start with `kit_cli_commands/`
3. **Description**: non-empty string
4. **No directory traversal**: path cannot contain `..`

### Warning Sources

If you see warnings during kit loading, check:

1. **"does not have expected function"** - Function name doesn't match command name (see naming convention above)
2. **"Command file not found"** - Path in kit.yaml doesn't exist
3. **"Failed to import command"** - Python import error in the command file
4. **"Invalid command"** - Validation error (name format, path, description)
```

## Verification

1. Run `dot-agent run erk --help` - should list commands without warnings
2. Run `dot-agent run erk get-closing-text` in a worktree with `.impl/issue.json` - should output closing text
3. Run `dot-agent run erk get-closing-text` in a directory without `.impl/issue.json` - should have no output