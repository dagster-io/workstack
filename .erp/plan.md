# Fix Kit CLI Command Function Name Warnings

## Problem

Two kit CLI commands have mismatched function names that cause warnings during kit loading:

1. Command `post-plan-comment` expects function `post_plan_comment` but has `post_plan_issue_comment`
2. Command `get-closing-text` expects function `get_closing_text` but has `get_closing_text_command`

## Root Cause

The kit command loader converts command names from kebab-case to snake_case to find the corresponding Python function. The validation code does:

```python
function_name = command_def.name.replace("-", "_")
if not hasattr(module, function_name):
    # Warning is printed
```

## Solution

Rename the Python functions to match the expected snake_case conversion of their command names.

## Implementation Steps

### 1. Fix post_plan_comment.py

**File:** `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_plan_comment.py`

- Line 29: Rename function `post_plan_issue_comment` → `post_plan_comment`
- Line 112: Update function call in `__main__` block from `post_plan_issue_comment()` → `post_plan_comment()`

### 2. Fix get_closing_text.py

**File:** `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/get_closing_text.py`

- Line 39: Rename function `get_closing_text_command` → `get_closing_text`
- No `__main__` block exists in this file

### 3. Verify the fix

Run a command that loads kits and verify no warnings appear:

```bash
dot-agent kit list
```

## Context & Understanding

### Kit CLI Command Naming Convention

The convention is simple: command name (kebab-case) → Python function name (snake_case) by replacing hyphens with underscores.

**Examples from codebase:**

- Command `find-project-dir` → Function `find_project_dir()` ✅
- Command `create-issue` → Function `create_issue()` ✅
- Command `format-error` → Function `format_error()` ✅

### Files NOT Requiring Changes

- **kit.yaml files**: Already reference correct command names (kebab-case), not function names
- **Tests**: No test files exist for these commands
- **Documentation**: Only references command names, not Python function names
- **Agent markdown**: References CLI command names like `dot-agent run erk get-closing-text`, not function names

### Impact

- Eliminates warning messages during kit command loading
- No functional changes to command behavior
- No breaking changes to CLI interface

## Validation

After making changes, verify:

1. No warnings when running `dot-agent kit list`
2. Commands still work: `dot-agent run erk get-closing-text` and `dot-agent run erk post-plan-comment`
3. Type checking passes: `uv run pyright` on both files
