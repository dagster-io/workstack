# /agent-inspect [agent-id] [--type <type>] [--full]

Quick access to agent execution details with performance metrics.

Inspects agent runs from the current Claude Code session, showing performance metrics like token usage, execution duration, cost estimates, and error recovery patterns.

## Usage

```bash
# List all agents in current session
/agent-inspect

# Show specific agent by ID (prefix match)
/agent-inspect bffe43

# Filter by agent type
/agent-inspect --type git-branch-submitter

# Filter by agent type with full output (not truncated)
/agent-inspect --type devrun --full
```

## What You'll See

**Summary view** (no agent-id specified):

- Table of all agents with: ID, type, task description, duration, tokens, cost, status
- Performance metrics at a glance

**Detail view** (agent-id specified):

- Full task description
- Performance metrics: tokens (input/output/cached), duration, cost, cache efficiency
- Complete list of tool calls with status (✅/❌)
- Error details and recovery patterns
- Token usage by API call

## Options

- `[agent-id]`: Show specific agent (prefix match on agent ID)
- `--type <agent-type>`: Filter to specific agent type (e.g., devrun, git-branch-submitter)
- `--full`: Include complete tool outputs (not truncated to 500 chars)
- `--all`: Show all agents including successful ones (default shows failed + recent)

## How It Works

1. Auto-detects session ID from SESSION_CONTEXT environment variable
2. Finds agent log files in `~/.claude/projects/`
3. Parses JSONL logs to extract execution details
4. Calculates performance metrics from Claude API usage data
5. Displays results in rich terminal UI with tables and panels

## Examples

**List all agents from current session:**

```bash
/agent-inspect
```

Output:

```
Agent ID  Type              Task (truncated)        Duration  Tokens  Cost    Status
abc123    devrun            Run fast CI checks      12.3s     15.2K   $0.023  ✅
bffe4320  git-branch-sub... Execute submit...       32.1s     16.3K   $0.025  ✅
```

**Inspect specific agent:**

```bash
/agent-inspect bffe4320
```

Output shows detailed performance metrics, token usage breakdown, and complete tool call history.

**Filter by agent type:**

```bash
/agent-inspect --type git-branch-submitter
```

Shows only git-branch-submitter agents from the current session.

---

## Agent Instructions

You are helping the user inspect agent execution details with a focus on performance analysis.

### Steps

1. **Extract session ID** from SESSION_CONTEXT environment variable
   - Look for: `SESSION_CONTEXT: session_id=<uuid>`
   - Extract the UUID portion

2. **Parse command arguments**
   - Check for positional agent-id argument
   - Check for `--type <agent-type>` flag
   - Check for `--full` flag
   - Check for `--all` flag

3. **Run the debug-agent command** with appropriate flags:

```bash
python -m erk.data.kits.erk.kit_cli_commands.erk.debug_agent \
  --session-id <session-id> \
  --all \
  [--agent-type <type>] \
  [--agent-id <id>] \
  [--full]
```

4. **Display the output** directly to the user
   - The debug_agent.py module handles Rich UI formatting
   - Performance metrics are included automatically
   - No need to post-process the output

### Example Execution

**User runs:** `/agent-inspect --type git-branch-submitter`

**Your actions:**

1. Extract session ID: `ffa93816-a3a5-4341-bff6-aada29be64b5`
2. Run command:
   ```bash
   python -m erk.data.kits.erk.kit_cli_commands.erk.debug_agent \
     --session-id ffa93816-a3a5-4341-bff6-aada29be64b5 \
     --all \
     --agent-type git-branch-submitter
   ```
3. Display the rich terminal output to user

### Error Handling

**If session ID not found:**

```
Error: Could not detect session ID from context.

The /agent-inspect command requires running within a Claude Code session.
Alternatively, you can specify a session ID manually:

  /agent-inspect --session-id <uuid>
```

**If no agents match filters:**

```
No agents found matching the specified criteria.

Try:
  /agent-inspect              # List all agents
  /agent-inspect --all        # Include successful agents
```

## Important Notes

- Session ID is auto-detected from SESSION_CONTEXT (set by session-id-injector-hook)
- Performance metrics include token costs based on Claude API pricing
- Agent type detection has been improved to reduce "unknown" entries
- Rich terminal UI requires terminal with color support
- Full output (`--full` flag) may be very long for agents with many tool calls
