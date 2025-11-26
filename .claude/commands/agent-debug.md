# /agent-debug

Inspect failed agent runs from the current session and display results as structured Markdown.

When agents fail during execution, this command analyzes their logs and presents failures in a readable format that can be copied, shared, or referenced.

## Usage

```bash
/agent-debug
```

The command auto-detects the current session ID and shows all failed agents with their errors.

## What You'll See

The output includes:

- Failed agent types and execution times
- Tool calls that produced errors
- Exit codes and error messages
- Command details for bash failures

All formatted as clean Markdown that you can copy and use elsewhere.

## Implementation

This command uses the `debug-agent` kit CLI command to parse agent logs and format them for display.

---

You are a debugging assistant. Your task is to inspect failed agent runs from the current session and present the findings as structured Markdown.

## Steps

1. **Extract session ID** from the SESSION_CONTEXT environment variable that's injected by the session-id-injector-hook
   - Look for the reminder in conversation context: `SESSION_CONTEXT: session_id=<uuid>`
   - Extract just the UUID portion

2. **Call the debug-agent CLI tool** with JSON output:

   ```bash
   dot-agent run erk debug-agent --session-id <session-id> --json
   ```

3. **Parse the JSON response** which has this structure:

   ```json
   {
     "session_id": "...",
     "agents": [
       {
         "agent_id": "...",
         "agent_type": "...",
         "started_at": "...",
         "status": "failed",
         "task_description": "...",
         "tool_calls": [
           {
             "tool": "Bash",
             "tool_id": "...",
             "input": { "command": "..." },
             "result": "...",
             "exit_code": 2,
             "error": "..."
           }
         ]
       }
     ]
   }
   ```

4. **Format as Markdown** with this structure:

```markdown
# Agent Debugging Report

**Session**: `<session-id-first-8-chars>...`

## Failed Agents

### <agent-type> (agent-<agent-id-first-8-chars>)

**Started**: <started_at>
**Status**: Failed

**Task Description**:
```

<first 300 chars of task_description>

````

**Failed Operations**:

1. **<tool-name>**: `<command or description>`
   - Exit code: `<exit_code>`
   - Error:
     ```
     <error message>
     ```

[Repeat for each failed tool call]

---

[Repeat for each failed agent]
````

5. **Handle edge cases**:
   - If no session ID found: "Error: Could not detect session ID from context"
   - If no failed agents: "No failed agents found in this session"
   - If CLI command fails: Show the error message

6. **Present the formatted Markdown** directly in the conversation

## Example Output

Here's what the formatted output should look like:

```markdown
# Agent Debugging Report

**Session**: `27767906...`

## Failed Agents

### devrun (agent-abc12345)

**Started**: 2025-11-23 14:32:15
**Status**: Failed

**Task Description**:
```

Run pytest tests and fix any failures

````

**Failed Operations**:

1. **Bash**: `pytest tests/unit/test_foo.py`
   - Exit code: `1`
   - Error:
     ```
     FAILED tests/unit/test_foo.py::test_bar - AssertionError: expected 5 got 3
     ```

---

### gt-branch-submitter (agent-def67890)

**Started**: 2025-11-23 14:35:22
**Status**: Failed

**Task Description**:
````

Execute simplified Graphite submit workflow

````

**Failed Operations**:

1. **Bash**: `gt stack submit`
   - Exit code: `2`
   - Error:
     ```
     Error: No commits to submit
     ```
````

## Important Notes

- Only show failed agents (status = "failed")
- Truncate long error messages to keep output readable
- Use code blocks for commands and errors
- Keep the format clean and copy-paste friendly
- Present the Markdown directly - don't explain what you're doing, just show the report
