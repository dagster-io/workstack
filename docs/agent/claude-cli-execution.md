# Programmatic Claude CLI Execution

This document describes how to invoke Claude CLI programmatically from Python code, including streaming output handling and result collection.

## Overview

The `ClaudeExecutor` abstraction (`src/erk/core/claude_executor.py`) provides a clean interface for executing Claude CLI commands from Python, enabling:

- **Dependency injection** for testing without mock.patch
- **Streaming execution** with real-time event processing
- **Interactive mode** via process replacement (os.execvp)
- **Non-interactive mode** via subprocess with output parsing

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Command Layer                        │
│  (e.g., pr/submit_cmd.py, implement.py)                     │
│                                                             │
│  Uses: execute_streaming_command() or                       │
│        execute_streaming_commands() helpers                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Shared Execution Helpers                      │
│  src/erk/cli/claude_helpers.py                              │
│                                                             │
│  - execute_streaming_command() - single command             │
│  - execute_streaming_commands() - multiple commands         │
│  - Rich console spinner                                     │
│  - StreamEvent processing                                   │
│  - CommandResult collection                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ClaudeExecutor (ABC)                       │
│  src/erk/core/claude_executor.py                            │
│                                                             │
│  - is_claude_available()                                    │
│  - execute_command_streaming() → Iterator[StreamEvent]      │
│  - execute_command() → CommandResult                        │
│  - execute_interactive()                                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   RealClaudeExecutor    │     │   FakeClaudeExecutor    │
│   (Production)          │     │   (Testing)             │
│                         │     │                         │
│   Uses subprocess.Popen │     │   Returns canned events │
└─────────────────────────┘     └─────────────────────────┘
```

## Key Types

### StreamEvent

Events emitted during streaming execution:

```python
@dataclass
class StreamEvent:
    event_type: str  # "text", "tool", "spinner_update", "pr_url", "error"
    content: str     # The event payload
```

| Event Type       | Description                | Example Content                |
| ---------------- | -------------------------- | ------------------------------ |
| `text`           | Text output from Claude    | "Creating pull request..."     |
| `tool`           | Tool use summary           | "Edit: src/foo.py (3 lines)"   |
| `spinner_update` | Status for spinner display | "Running pytest..."            |
| `pr_url`         | Extracted PR URL           | "https://github.com/org/r/123" |
| `error`          | Error occurred             | "Command failed with exit 1"   |

### CommandResult

Final result after command completion:

```python
@dataclass
class CommandResult:
    success: bool
    pr_url: str | None
    duration_seconds: float
    error_message: str | None
    filtered_messages: list[str]
```

## Usage Patterns

### Pattern 1: Single Command with Streaming (Recommended)

For commands that execute a single Claude slash command with real-time output.

**Example:** `src/erk/cli/commands/pr/submit_cmd.py`

```python
from erk.cli.claude_helpers import execute_streaming_command

@click.command("submit")
@click.option("--dangerous", is_flag=True)
@click.option("--verbose", is_flag=True)
@click.pass_obj
def pr_submit(ctx: ErkContext, dangerous: bool, verbose: bool) -> None:
    """Submit current branch as a pull request."""
    result = execute_streaming_command(
        executor=ctx.claude_executor,
        command="/gt:submit-pr",
        worktree_path=ctx.cwd,
        dangerous=dangerous,
        verbose=verbose,
    )

    # Handle result (display PR URL, check for errors)
    if result.pr_url:
        console.print(f"PR created: {result.pr_url}")
    if not result.success:
        raise click.ClickException("PR submission failed")
```

### Pattern 2: Multiple Commands in Sequence

For workflows that run multiple slash commands, stopping on first failure.

**Example:** `src/erk/cli/commands/implement.py` (via `_execute_non_interactive_mode`)

```python
from erk.cli.claude_helpers import execute_streaming_commands

commands = ["/erk:implement-plan", "/fast-ci", "/gt:submit-pr"]
all_results = execute_streaming_commands(
    executor=ctx.claude_executor,
    commands=commands,
    worktree_path=worktree_path,
    dangerous=dangerous,
    verbose=verbose,
)

# all_results is list[CommandResult], execution stops on first failure
if not all(r.success for r in all_results):
    raise click.ClickException("One or more commands failed")
```

### Pattern 3: Interactive Mode (Process Replacement)

For handing off to Claude interactively (never returns):

```python
# This replaces the current process with Claude
executor.execute_interactive(worktree_path, dangerous=False)
# Never reaches here - process is replaced
```

### Pattern 4: Non-Streaming (Simple Result)

When you don't need real-time output:

```python
result = executor.execute_command(
    command="/gt:submit-pr",
    worktree_path=worktree_path,
    dangerous=False,
    verbose=False,
)
if result.success:
    print(f"PR: {result.pr_url}")
```

## Implementation Details

### Claude CLI Flags

The executor uses these flags for non-interactive execution:

```bash
claude --print --verbose --permission-mode acceptEdits --output-format stream-json [command]
```

- `--print`: Output results to stdout
- `--verbose`: Include detailed output
- `--permission-mode acceptEdits`: Auto-accept file edits
- `--output-format stream-json`: JSON lines for parsing
- `--dangerously-skip-permissions`: (optional) Skip all permission prompts

### Stream JSON Parsing

The `RealClaudeExecutor._parse_stream_json_line()` method extracts:

1. **Text content** from `assistant_message` events
2. **Tool summaries** from `tool_use` items
3. **Spinner updates** for status display
4. **PR URLs** from `tool_result` content

### Error Handling

Errors are captured as `StreamEvent(event_type="error", content=...)` and propagate to `CommandResult.success=False`.

## Testing

Use `FakeClaudeExecutor` for testing:

```python
from tests.fakes.claude_executor import FakeClaudeExecutor

def test_pr_submit():
    executor = FakeClaudeExecutor()
    executor.set_streaming_events([
        StreamEvent("text", "Creating PR..."),
        StreamEvent("pr_url", "https://github.com/org/repo/pull/123"),
    ])

    # Test your command with fake executor
    result = executor.execute_command("/gt:submit-pr", Path("/tmp"), False)
    assert result.success
    assert result.pr_url == "https://github.com/org/repo/pull/123"
```

## Anti-Patterns

### ❌ Don't: Duplicate Streaming Logic

```python
# ❌ WRONG: Copy-pasting streaming loop from implement.py
with console.status(...) as status:
    for event in executor.execute_command_streaming(...):
        if event.event_type == "text":
            console.print(event.content)
        # ... 50 lines of duplicated code
```

### ✅ Do: Use Shared Helper

```python
# ✅ CORRECT: Reuse shared helper
execute_streaming_command(
    executor=ctx.claude_executor,
    command="/gt:submit-pr",
    worktree_path=ctx.cwd,
    dangerous=dangerous,
    verbose=verbose,
)
```

### ❌ Don't: Call Claude CLI Directly

```python
# ❌ WRONG: Bypasses abstraction, hard to test
subprocess.run(["claude", "--print", "/gt:submit-pr"])
```

### ✅ Do: Use Executor

```python
# ✅ CORRECT: Testable, consistent error handling
result = ctx.claude_executor.execute_command("/gt:submit-pr", ctx.cwd, False)
```

## Related Documentation

- [subprocess-wrappers.md](subprocess-wrappers.md) - General subprocess execution patterns
- [command-agent-delegation.md](command-agent-delegation.md) - Delegating from slash commands to agents
- [erk-architecture.md](erk-architecture.md) - Dependency injection patterns
