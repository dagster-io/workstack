---
erk_plan: true
created_at: 2025-11-23T13:29:24.673588+00:00
---

## Fix Session Plan Extraction and Add Integration Tests

**Problems:**

1. **Path construction bug:** Dots in paths not converted to hyphens (`.erk` → `-.erk` but should be `--erk`)
2. **Agent files excluded:** Plans in `agent-*.jsonl` files are skipped
3. **No integration tests:** No tests with realistic session file fixtures

**Solution:** Fix both bugs, add comprehensive integration tests with realistic session data fixtures.

### Changes Required

1. **Fix `get_claude_project_dir()` in `session_plan_extractor.py`**
   - Line 30: Replace dots with hyphens to match Claude's directory naming
   - Change: `working_dir.replace("/", "-")`
   - To: `working_dir.replace("/", "-").replace(".", "-")`
   - Update docstring with dot conversion example

2. **Remove agent file exclusion in `get_latest_plan_from_session()`**
   - Lines 97-102: Remove `and not f.name.startswith("agent-")` filter
   - Change: `if f.is_file() and not f.name.startswith("agent-")`
   - To: `if f.is_file()`
   - Update docstring to clarify agent files are included

3. **Add test fixtures to `tests/unit/kits/erk/fixtures.py`**
   - Add `JSONL_ASSISTANT_EXIT_PLAN_MODE` - Assistant message with ExitPlanMode
   - Add `SESSION_WITH_PLAN` - Complete session with plan
   - Add `SESSION_MULTIPLE_PLANS` - Multiple plans with different timestamps
   - Add `SESSION_AGENT_FILE_PLAN` - Plan in agent subprocess file
   - Add helper: `create_session_file(path, entries)` - Write JSONL

4. **Create integration test file `tests/integration/kits/erk/test_session_plan_extractor_integration.py`**
   - Test path construction with dots (`.erk`, `.config` directories)
   - Test finding plans in main session files
   - Test finding plans in agent files
   - Test multiple plans across files (verify timestamp sorting)
   - Test session_id filtering
   - Test project directory not found
   - Test no plans found
   - Test malformed JSON handling

5. **Create unit test file `tests/unit/kits/erk/test_session_plan_extractor.py`**
   - Test `get_claude_project_dir()` with various path formats
   - Test `extract_plan_from_session_line()` with valid/invalid data
   - Test `get_latest_plan_from_session()` with fixtures
   - Test `get_latest_plan()` integration entry point

### Test Structure

**Integration tests simulate:**

```
tmp_path/
├── .claude/
│   └── projects/
│       └── -Users-schrockn--erk-repos-erk/  # Note: dots → hyphens
│           ├── session-123.jsonl           # Main session
│           ├── agent-abc123.jsonl          # Agent subprocess
│           └── 9411604c-cceb.jsonl         # UUID session
└── Users/
    └── schrockn/
        └── .erk/
            └── repos/
                └── erk/                     # Working directory
```

**Realistic JSONL entries:**

```json
{
  "type": "assistant",
  "message": {
    "content": [
      {
        "type": "tool_use",
        "name": "ExitPlanMode",
        "input": { "plan": "# Plan text" }
      }
    ]
  },
  "timestamp": "2025-11-23T10:00:00.000Z"
}
```

### Implementation Notes

- **Pattern from existing tests:** Use `tmp_path`, `monkeypatch` for `Path.home()`
- **JSONL format:** One JSON object per line, newline-separated
- **Timestamp sorting:** ISO 8601 format for proper lexicographic sorting
- **Error handling:** Tests verify graceful degradation (skip malformed lines)
- **Agent files:** Critical for Plan agent workflow - must be included
