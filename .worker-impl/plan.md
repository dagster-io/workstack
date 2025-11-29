# Plan: Remove "state" Column from `erk run list`

## Problem

The `erk run list` command displays a "state" column with width 4, causing the header to truncate to "sta…" in the Rich table.

## Solution

Remove the "state" column entirely. The plan column already provides a link to the issue where users can see the state.

## Changes Required

### 1. `src/erk/cli/commands/run/list_cmd.py`

**Remove column definition (line 92):**

```python
table.add_column("state", no_wrap=True, width=4)  # DELETE THIS LINE
```

**Remove state_cell assignments and usage:**

- Line 127: `state_cell = "[dim]X[/dim]"` - DELETE
- Line 147: `state_cell = get_issue_state_emoji(issue.state)` - DELETE
- Line 155: `state_cell = "[dim]-[/dim]"` - DELETE
- Line 178: `state_cell,` from `table.add_row()` - DELETE

**Remove unused import (line 4):**

```python
from erk_shared.github.emoji import get_checks_status_emoji, get_issue_state_emoji
# Change to:
from erk_shared.github.emoji import get_checks_status_emoji
```

### 2. `tests/commands/run/test_list.py`

**Delete test function `test_list_runs_displays_issue_state` (lines 724-795):**
This test specifically verifies the state column shows 🟢 for OPEN and 🔴 for CLOSED issues. Since we're removing the column, this test should be deleted.

**Delete test function `test_list_runs_legacy_runs_show_x_for_state` (lines 798-836):**
This test verifies legacy runs show "X" in the state column. Since we're removing the column, this test should be deleted.

## Verification

Run scoped tests:

```bash
uv run pytest tests/commands/run/test_list.py
```
