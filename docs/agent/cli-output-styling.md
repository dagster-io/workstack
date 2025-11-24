# CLI Output Styling Guide

This guide defines the standard color scheme, emoji conventions, and output abstraction patterns for erk CLI commands.

## Color Conventions

Use consistent colors and styling for CLI output via `click.style()`:

| Element                  | Color            | Bold | Example                                             |
| ------------------------ | ---------------- | ---- | --------------------------------------------------- |
| Branch names             | `yellow`         | No   | `click.style(branch, fg="yellow")`                  |
| PR numbers               | `cyan`           | No   | `click.style(f"PR #{pr}", fg="cyan")`               |
| PR titles                | `bright_magenta` | No   | `click.style(title, fg="bright_magenta")`           |
| Plan titles              | `cyan`           | No   | `click.style(f"📋 {plan}", fg="cyan")`              |
| Success messages (✓)     | `green`          | No   | `click.style("✓ Done", fg="green")`                 |
| Section headers          | -                | Yes  | `click.style(header, bold=True)`                    |
| Current/active branches  | `bright_green`   | Yes  | `click.style(branch, fg="bright_green", bold=True)` |
| Paths (after completion) | `green`          | No   | `click.style(str(path), fg="green")`                |
| Paths (metadata)         | `white`          | Dim  | `click.style(str(path), fg="white", dim=True)`      |
| Error states             | `red`            | No   | `click.style("Error", fg="red")`                    |
| Dry run markers          | `bright_black`   | No   | `click.style("(dry run)", fg="bright_black")`       |
| Worktree/stack names     | `cyan`           | Yes  | `click.style(name, fg="cyan", bold=True)`           |

## Clickable Links (OSC 8)

The CLI supports clickable terminal links using OSC 8 escape sequences for PR numbers, plan IDs, and issue references.

### When to Use

Make IDs clickable when:

- A URL is available for the resource
- The ID is user-facing (e.g., PR numbers, plan IDs, issue numbers)
- Clicking would provide value (navigate to GitHub, external tracker, etc.)

### Implementation Pattern

**For simple text output (user_output):**

```python
# Format: \033]8;;URL\033\\text\033]8;;\033\\
id_text = f"#{identifier}"
if url:
    colored_id = click.style(id_text, fg="cyan")
    clickable_id = f"\033]8;;{url}\033\\{colored_id}\033]8;;\033\\"
else:
    clickable_id = click.style(id_text, fg="cyan")

user_output(f"Issue: {clickable_id}")
```

**For Rich tables:**

```python
from rich.table import Table

# Rich supports OSC 8 via markup syntax
id_text = f"#{identifier}"
if url:
    issue_id = f"[link={url}][cyan]{id_text}[/cyan][/link]"
else:
    issue_id = f"[cyan]{id_text}[/cyan]"

table.add_row(issue_id, ...)
```

### Styling Convention

- **Clickable IDs**: Use cyan color (`fg="cyan"`) to indicate interactivity
- **Non-clickable IDs**: Use cyan for consistency, but without OSC 8 wrapper
- This matches the existing PR link styling pattern

### Examples in Codebase

- `src/erk/core/display_utils.py` - `format_pr_info()` function (reference implementation)
- `src/erk/cli/commands/plan/list_cmd.py` - Clickable plan IDs in table
- `src/erk/cli/commands/plan/get.py` - Clickable plan ID in details
- `src/erk/status/renderers/simple.py` - Clickable issue numbers in status

### Terminal Compatibility

- Most modern terminals support OSC 8 (iTerm2, Terminal.app, Kitty, Alacritty, WezTerm, etc.)
- On unsupported terminals, links display as normal colored text
- No action required for graceful degradation

## Emoji Conventions

Standard emojis for CLI output:

- `✓` - Success indicators
- `✅` - Major success/completion
- `❌` - Errors/failures
- `📋` - Lists/plans
- `🗑️` - Deletion operations
- `⭕` - Aborted/cancelled
- `ℹ️` - Info notes

## Spacing Guidelines

- Use empty `click.echo()` for vertical spacing between sections
- Use `\n` prefix in strings for section breaks
- Indent list items with `  ` (2 spaces)

## Output Abstraction

**Use output abstraction for all CLI output to separate user messages from machine-readable data.**

### Functions

- `user_output()` - Routes to stderr for user-facing messages
- `machine_output()` - Routes to stdout for shell integration data

**Import:** `from erk.cli.output import user_output, machine_output`

### When to Use Each

| Use case                  | Function           | Rationale                   |
| ------------------------- | ------------------ | --------------------------- |
| Status messages           | `user_output()`    | User info, goes to stderr   |
| Error messages            | `user_output()`    | User info, goes to stderr   |
| Progress indicators       | `user_output()`    | User info, goes to stderr   |
| Success confirmations     | `user_output()`    | User info, goes to stderr   |
| Shell activation scripts  | `machine_output()` | Script data, goes to stdout |
| JSON output (--json flag) | `machine_output()` | Script data, goes to stdout |
| Paths for script capture  | `machine_output()` | Script data, goes to stdout |

### Example

```python
from erk.cli.output import user_output, machine_output

# User-facing messages
user_output(f"✓ Created worktree {name}")
user_output(click.style("Error: ", fg="red") + "Branch not found")

# Script/machine data
machine_output(json.dumps(result))
machine_output(str(activation_path))
```

## Reference Implementations

See these commands for examples:

- `src/erk/cli/commands/sync.py` - Uses custom `_emit()` helper
- `src/erk/cli/commands/jump.py` - Uses both user_output() and machine_output()
- `src/erk/cli/commands/consolidate.py` - Uses both abstractions

## See Also

- [cli-script-mode.md](cli-script-mode.md) - Script mode for shell integration (suppressing diagnostics)
