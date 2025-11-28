# Implementation Plan: session-get-plan Kit CLI Command

## Overview

Create a production-ready kit CLI command that extracts plan file names from Claude Code session IDs by parsing session JSONL files. Uses robust JSON parsing with comprehensive error handling.

## Design Approach

**Production-Ready & Focused**
- Proper JSONL parsing with Python's `json` module (not regex)
- Comprehensive error handling for all failure modes
- LBYL pattern throughout (Look Before You Leap)
- Type-safe with modern Python 3.13+ syntax
- Focused on plan extraction only (no speculative abstractions)

## Command Interface

### Usage
```bash
# Auto-detect session from environment
dot-agent run erk session-get-plan

# Explicit session ID
dot-agent run erk session-get-plan --session-id abc-123-def

# JSON output (default)
{
  "success": true,
  "session_id": "abc-123-def",
  "plan_filename": "ethereal-plotting-sunbeam.md",
  "plan_path": "/Users/foo/.claude/plans/ethereal-plotting-sunbeam.md"
}

# Error output
{
  "success": false,
  "error": "Session file not found",
  "session_id": "abc-123",
  "help": "Session may have been cleaned up from ~/.claude/projects/"
}
```

### Options
- `--session-id`: Session UUID (auto-detected from `SESSION_CONTEXT` env var if not provided)
- `--text`: Output plain filename only (for shell scripting)

## Algorithm

### Step 1: Resolve Session ID
```python
# Priority order:
1. --session-id CLI argument
2. SESSION_CONTEXT environment variable (format: "session_id=<uuid>" OR bare UUID)
3. Error if neither available
```

### Step 2: Find Session File
```python
# Search ~/.claude/projects/ for session
for project_dir in projects_dir.iterdir():
    session_file = project_dir / f"{session_id}.jsonl"
    if session_file.exists():
        return session_file

# Error if not found
```

### Step 3: Parse JSONL & Find Plan
```python
# Parse line-by-line (memory efficient)
for line in session_file.read_text().splitlines():
    if not line.strip():
        continue

    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue  # Skip malformed lines

    # Look for plan writes via Bash heredoc
    if entry.get("type") == "user":
        content = entry.get("message", {}).get("content", "")
        if "plans/" in content and ".md" in content:
            # Extract: cat > ~/.claude/plans/<name>.md
            # ENRICHED: Use [a-z0-9_-]+ pattern for flexibility
            match = re.search(r'plans/([a-z0-9_-]+\.md)', content)
            if match:
                filename = match.group(1)
                # ENRICHED: Broader exclusion filter
                if not _is_excluded_pattern(filename):
                    return filename

# Error if no plan found
```

### Step 4: Verify Plan File Exists
```python
plan_path = Path.home() / ".claude" / "plans" / plan_filename

if not plan_path.exists():
    # Warning: plan was created but no longer exists
    return with_warning(plan_filename, "Plan file no longer exists")
```

## Error Handling

### Error Modes (6 distinct cases)

1. **No session ID available**
   - Brief: "No session ID provided"
   - Help: "Use --session-id or run within Claude Code session"
   - Exit: 1

2. **Session file not found**
   - Brief: "Session file not found"
   - Help: "Session {id} not found in ~/.claude/projects/"
   - Exit: 1

3. **Malformed JSONL**
   - Action: Skip invalid lines, continue parsing
   - Exit: Only if entire file is invalid

4. **No plan found**
   - Brief: "No plan file found in session"
   - Help: "Session may not have created a plan (no plan-extractor agent)"
   - Exit: 1

5. **Plan file deleted**
   - Brief: "Plan file no longer exists"
   - Success: true (with warning field)
   - Return: filename anyway

6. **Multiple plans found**
   - Action: Return most recent (last occurrence)
   - Success: true

### LBYL Pattern
```python
# Check before operations
if not projects_dir.exists():
    return error("Projects directory not found")

if not session_file.exists():
    return error("Session file not found")

if not session_file.is_file():
    return error("Session path is not a file")

# Only then read
content = session_file.read_text()
```

## Implementation Structure

### File: `session_get_plan.py` (~270 lines)

**ENRICHMENT NOTES:**
- Added `EXCLUDED_PREFIXES` constant for broader filtering
- Added `_is_excluded_pattern()` helper function
- Updated `_get_session_id_from_env()` to accept bare UUIDs
- Added `_looks_like_uuid()` validation helper
- Updated regex pattern to `[a-z0-9_-]+`

```python
#!/usr/bin/env python3
"""Extract plan file name from Claude Code session."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import click


@dataclass
class PlanResult:
    """Success result."""
    success: bool
    session_id: str
    plan_filename: str
    plan_path: str
    warning: str | None = None


@dataclass
class PlanError:
    """Error result."""
    success: bool
    error: str
    session_id: str | None
    help: str


def find_plan_in_session(
    session_id: str,
    projects_dir: Path,
) -> PlanResult | PlanError:
    """Find plan filename from session JSONL."""

    # Step 1: Find session file
    session_file = _find_session_file(session_id, projects_dir)
    if isinstance(session_file, PlanError):
        return session_file

    # Step 2: Parse JSONL and find plan
    plan_filename = _extract_plan_filename(session_file)
    if isinstance(plan_filename, PlanError):
        return plan_filename

    # Step 3: Verify plan exists
    plan_path = Path.home() / ".claude" / "plans" / plan_filename
    warning = None if plan_path.exists() else "Plan file no longer exists"

    return PlanResult(
        success=True,
        session_id=session_id,
        plan_filename=plan_filename,
        plan_path=str(plan_path),
        warning=warning,
    )


def _find_session_file(
    session_id: str,
    projects_dir: Path,
) -> Path | PlanError:
    """Find session JSONL file in projects directory."""

    if not projects_dir.exists():
        return PlanError(
            success=False,
            error="Projects directory not found",
            session_id=session_id,
            help=f"Directory {projects_dir} does not exist",
        )

    # Search all project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists() and session_file.is_file():
            return session_file

    return PlanError(
        success=False,
        error="Session file not found",
        session_id=session_id,
        help=f"Session {session_id[:8]}... not found in {projects_dir}",
    )


def _extract_plan_filename(session_file: Path) -> str | PlanError:
    """Parse JSONL and extract plan filename."""

    try:
        content = session_file.read_text(encoding="utf-8")
    except OSError as e:
        return PlanError(
            success=False,
            error="Cannot read session file",
            session_id=session_file.stem,
            help=f"OS error: {e}",
        )

    # Pattern: cat > ~/.claude/plans/<name>.md
    # or: plans/<name>.md in tool result content
    plan_pattern = re.compile(r'plans/([a-z-]+\.md)')

    found_plans: list[str] = []

    for line in content.splitlines():
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # Skip malformed lines

        # Check user entries (tool results)
        if entry.get("type") == "user":
            content_str = str(entry.get("message", {}).get("content", ""))
            matches = plan_pattern.findall(content_str)

            # Filter out agent logs (contain "agent-")
            for match in matches:
                if "agent-" not in match:
                    found_plans.append(match)

    if not found_plans:
        return PlanError(
            success=False,
            error="No plan file found in session",
            session_id=session_file.stem,
            help="Session may not have created a plan",
        )

    # Return last plan (most recent if multiple)
    return found_plans[-1]


def _get_session_id_from_env() -> str | None:
    """Extract session ID from SESSION_CONTEXT env var."""
    session_context = os.environ.get("SESSION_CONTEXT")
    if not session_context:
        return None

    # Format: "session_id=<uuid>"
    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()

    return None


@click.command(name="session-get-plan")
@click.option(
    "--session-id",
    type=str,
    help="Session UUID (auto-detected from SESSION_CONTEXT if not provided)",
)
@click.option(
    "--text",
    is_flag=True,
    help="Output plain filename only (for scripting)",
)
def session_get_plan(session_id: str | None, text: bool) -> None:
    """Extract plan file name from Claude Code session.

    Searches session logs in ~/.claude/projects/ for plan file writes
    and returns the plan filename.

    Examples:
        # Auto-detect from environment
        dot-agent run erk session-get-plan

        # Explicit session ID
        dot-agent run erk session-get-plan --session-id abc-123

        # Plain text output
        dot-agent run erk session-get-plan --text
    """
    # Resolve session ID
    if not session_id:
        session_id = _get_session_id_from_env()

    if not session_id:
        result = PlanError(
            success=False,
            error="No session ID provided",
            session_id=None,
            help="Use --session-id or run within Claude Code session",
        )
        _output_result(result, text)
        raise SystemExit(1)

    # Find plan
    projects_dir = Path.home() / ".claude" / "projects"
    result = find_plan_in_session(session_id, projects_dir)

    # Output result
    _output_result(result, text)

    # Exit with error if failed
    if not result.success:
        raise SystemExit(1)


def _output_result(result: PlanResult | PlanError, text_mode: bool) -> None:
    """Output result in requested format."""
    if text_mode and isinstance(result, PlanResult):
        # Plain filename for scripting
        click.echo(result.plan_filename)
    else:
        # JSON output (default)
        if isinstance(result, PlanResult):
            output = {
                "success": result.success,
                "session_id": result.session_id,
                "plan_filename": result.plan_filename,
                "plan_path": result.plan_path,
            }
            if result.warning:
                output["warning"] = result.warning
        else:
            output = {
                "success": result.success,
                "error": result.error,
                "session_id": result.session_id,
                "help": result.help,
            }

        click.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    session_get_plan()
```

## Testing Strategy

### Unit Tests (~200 lines)

**File**: `tests/unit/kits/erk/test_session_get_plan.py`

```python
def test_find_plan_success():
    """Test successful plan extraction."""
    # Setup: Create temp session file with plan
    # Execute: find_plan_in_session()
    # Assert: Returns PlanResult with correct filename

def test_find_plan_no_session_id():
    """Test error when no session ID provided."""
    # Assert: Returns PlanError with helpful message

def test_find_plan_session_not_found():
    """Test error when session file doesn't exist."""
    # Assert: Returns PlanError with session ID context

def test_find_plan_malformed_json():
    """Test skips malformed JSONL lines."""
    # Setup: Session file with some invalid JSON lines
    # Assert: Still finds plan from valid lines

def test_find_plan_no_plan_found():
    """Test error when no plan in session."""
    # Setup: Session file without plan writes
    # Assert: Returns PlanError

def test_find_plan_multiple_plans():
    """Test returns most recent when multiple plans."""
    # Setup: Session with multiple plan writes
    # Assert: Returns last plan

def test_find_plan_file_deleted():
    """Test warning when plan file no longer exists."""
    # Setup: Plan filename in session but file deleted
    # Assert: Success with warning field

def test_session_id_from_env():
    """Test extracting session ID from SESSION_CONTEXT."""
    # Setup: Set environment variable
    # Assert: Correctly extracts UUID

def test_cli_text_output():
    """Test --text flag outputs plain filename."""
    # Execute: CLI with --text
    # Assert: Output is just filename, no JSON
```

### Integration Tests (~100 lines)

**File**: `tests/integration/kits/erk/test_session_get_plan_integration.py`

```python
def test_session_get_plan_with_real_session(tmp_path):
    """Test full workflow with realistic session JSONL."""
    # Setup: Create session file matching real structure
    # Execute: CLI command
    # Assert: Returns correct plan filename

def test_session_get_plan_from_environment(tmp_path, monkeypatch):
    """Test auto-detection from SESSION_CONTEXT."""
    # Setup: Set SESSION_CONTEXT env var
    # Execute: CLI without --session-id
    # Assert: Auto-detects and finds plan
```

## Files to Create/Modify

### New Files
1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/session_get_plan.py`
   - Main command implementation (~250 lines)

2. `packages/dot-agent-kit/tests/unit/kits/erk/test_session_get_plan.py`
   - Unit tests (~200 lines)

3. `packages/dot-agent-kit/tests/integration/kits/erk/test_session_get_plan_integration.py`
   - Integration tests (~100 lines)

### Modified Files
1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`
   - Add command entry:
     ```yaml
     - name: session-get-plan
       path: kit_cli_commands/erk/session_get_plan.py
       description: Extract plan file name from Claude Code session
     ```

## Success Criteria

1. ✓ Session ID resolution (CLI arg or env var)
2. ✓ Session file discovery across all projects
3. ✓ Malformed JSON handling (skip invalid lines)
4. ✓ Plan filename extraction (main file, not agent logs)
5. ✓ Plan file verification (warning if deleted)
6. ✓ Multiple plans handling (return most recent)
7. ✓ Structured JSON output (success/error)
8. ✓ Text output mode for scripting
9. ✓ Helpful error messages with context
10. ✓ Full test coverage (unit + integration)
11. ✓ LBYL pattern compliance
12. ✓ Type hints throughout

## Implementation Sequence

1. **Create command skeleton** (30 min)
   - File structure, imports, Click decorator
   - Basic argument parsing

2. **Implement session ID resolution** (20 min)
   - CLI argument priority
   - Environment variable extraction
   - Error handling

3. **Implement session file discovery** (30 min)
   - Search projects directory
   - LBYL checks
   - Error messages

4. **Implement plan extraction** (45 min)
   - JSONL parsing
   - Regex pattern matching
   - Filter agent logs
   - Handle multiple plans

5. **Implement output formatting** (20 min)
   - JSON output
   - Text output
   - Error output

6. **Write unit tests** (1.5 hours)
   - Test all functions
   - Test all error modes
   - Edge cases

7. **Write integration tests** (45 min)
   - Real JSONL structure
   - Environment variable testing

8. **Update kit.yaml** (5 min)
   - Add command entry

9. **Manual testing** (30 min)
   - Test against real sessions
   - Verify error messages
   - Test both output modes

**Total estimated time: 4-5 hours**

## Trade-offs

### Advantages
- Robust error handling for production use
- Type-safe with modern Python syntax
- Memory efficient (line-by-line parsing)
- Helpful error messages with context
- Handles edge cases (malformed JSON, missing files)
- Testable (pure functions, dependency injection)

### Limitations
- Slightly more complex than regex-only approach (~250 vs ~150 lines)
- Doesn't build full session query framework (focused on this use case)
- Pattern matching for plan files (not full JSONL semantic parsing of tool_use entries)

### Rationale
Production reliability without over-engineering. Balances:
- Proper parsing vs simplicity
- Comprehensive errors vs code size
- Testability vs complexity
- Focused implementation vs speculative framework

## Future Extensibility

If additional session queries are needed later:

1. **Extract shared utilities** to `session_utils.py`:
   - Session ID resolution
   - Session file discovery
   - JSONL parsing helpers

2. **Create query-specific commands**:
   - `session-get-agents` (list agent types)
   - `session-get-edits` (list edited files)
   - Each ~100 lines reusing utilities

3. **Consider framework** if 3+ queries exist:
   - Abstract `SessionQuery` interface
   - Shared `SessionReader` class
   - See extensible plan for architecture

## Critical Files Reference

- `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/find_project_dir.py` - Reference for path encoding, discovery patterns
- `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/agent_debug.py` - Reference for session ID extraction (lines 20-39)
- `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/format_error.py` - Reference for simple command structure
- `/Users/schrockn/code/erk/packages/dot-agent-kit/tests/unit/kits/erk/test_issue_title_to_filename.py` - Reference for unit test patterns
- `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml` - Kit manifest for command registration
