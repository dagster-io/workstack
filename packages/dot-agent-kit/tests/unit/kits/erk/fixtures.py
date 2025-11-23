"""Test fixtures for session log preprocessing tests.

Contains real JSONL entry samples extracted from actual Claude Code session logs.
"""

# File history snapshot entry (should be filtered out)
JSONL_FILE_HISTORY_SNAPSHOT = """{
  "type": "file-history-snapshot",
  "messageId": "msg_123",
  "parentUuid": "parent_456",
  "sessionId": "session_789",
  "snapshot": {"trackedFileBackups": {}, "timestamp": "2025-11-20T00:00:00Z"},
  "isSnapshotUpdate": false,
  "timestamp": "2025-11-20T00:00:00.000Z",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "userType": "user",
  "isSidechain": false
}"""

# User message with string content
JSONL_USER_MESSAGE_STRING = """{
  "type": "user",
  "message": {"role": "user", "content": "Hello, how are you?"},
  "parentUuid": "parent_123",
  "sessionId": "session_456",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z",
  "userType": "user",
  "isSidechain": false
}"""

# User message with structured content
JSONL_USER_MESSAGE_STRUCTURED = """{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "Let me test <special> & chars"}]
  },
  "parentUuid": "parent_789",
  "sessionId": "session_abc",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Assistant message with text only
JSONL_ASSISTANT_TEXT = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "I'll help you with that."}],
    "usage": {"input_tokens": 100, "output_tokens": 50}
  },
  "parentUuid": "parent_def",
  "sessionId": "session_ghi",
  "gitBranch": "test-branch",
  "cwd": "/test/dir",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Assistant message with tool use
JSONL_ASSISTANT_TOOL_USE = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_abc123",
        "name": "Read",
        "input": {"file_path": "/test/file.py"}
      }
    ],
    "usage": {"input_tokens": 200, "output_tokens": 30}
  },
  "parentUuid": "parent_jkl",
  "sessionId": "session_mno",
  "gitBranch": "test-branch",
  "timestamp": "2025-11-20T00:00:00.000Z"
}"""

# Duplicate assistant message (for deduplication testing)
JSONL_DUPLICATE_ASSISTANT_TEXT = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "I'll help you with that."}]
  },
  "sessionId": "session_pqr"
}"""

# Duplicate assistant message with tool_use (should keep tool_use, drop text)
JSONL_DUPLICATE_ASSISTANT_WITH_TOOL = """{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "I'll help you with that."},
      {
        "type": "tool_use",
        "id": "toolu_xyz789",
        "name": "Edit",
        "input": {"file_path": "/test/edit.py"}
      }
    ]
  },
  "sessionId": "session_stu"
}"""

# Tool result
JSONL_TOOL_RESULT = """{
  "type": "tool_result",
  "message": {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_abc123",
        "content": "File contents:\\n     1→def hello():\\n     2→    print('Hello')"
      }
    ],
    "tool_use_id": "toolu_abc123"
  },
  "sessionId": "session_vwx"
}"""

# Expected XML outputs
EXPECTED_XML_USER_STRING = """  <user>Hello, how are you?</user>"""

EXPECTED_XML_USER_STRUCTURED = """  <user>Let me test &lt;special&gt; &amp; chars</user>"""

EXPECTED_XML_ASSISTANT_TEXT = """  <assistant>I'll help you with that.</assistant>"""

EXPECTED_XML_TOOL_USE = """  <tool_use name="Read" id="toolu_abc123">
    <param name="file_path">/test/file.py</param>
  </tool_use>"""

EXPECTED_XML_TOOL_RESULT = """  <tool_result tool="toolu_abc123">
File contents:
     1→def hello():
     2→    print('Hello')
  </tool_result>"""


# ExitPlanMode fixtures for plan extraction testing

# Assistant message with ExitPlanMode tool use
JSONL_ASSISTANT_EXIT_PLAN_MODE = (
    """{"type": "assistant", "message": {"role": "assistant", "content": ["""
    """{"type": "tool_use", "id": "toolu_plan123", "name": "ExitPlanMode", """
    """"input": {"plan": "## Fix Session Plan Extraction\\n\\n"""
    """**Problem:** Path construction doesn't handle dots.\\n\\n"""
    """**Solution:** Convert dots to hyphens.\\n\\n"""
    """### Changes Required\\n\\n1. Update path conversion logic\\n2. Add tests"}}], """
    """"usage": {"input_tokens": 500, "output_tokens": 200}}, """
    """"parentUuid": "parent_plan", "sessionId": "session_plan_test", """
    """"gitBranch": "fix-plan-extraction", "cwd": "/test/dir", """
    """"timestamp": "2025-11-23T10:00:00.000Z"}"""
)

# Second plan with later timestamp (for testing timestamp sorting)
JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER = (
    """{"type": "assistant", "message": {"role": "assistant", "content": ["""
    """{"type": "tool_use", "id": "toolu_plan456", "name": "ExitPlanMode", """
    """"input": {"plan": "## Updated Plan\\n\\n**Problem:** This is the newer plan.\\n\\n"""
    """**Solution:** Should be returned when multiple plans exist."}}]}, """
    """"sessionId": "session_plan_test2", "timestamp": "2025-11-23T12:00:00.000Z"}"""
)

# Earlier plan (for testing timestamp sorting)
JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER = (
    """{"type": "assistant", "message": {"role": "assistant", "content": ["""
    """{"type": "tool_use", "id": "toolu_plan789", "name": "ExitPlanMode", """
    """"input": {"plan": "## Old Plan\\n\\n**Problem:** This is the older plan.\\n\\n"""
    """**Solution:** Should NOT be returned when newer plan exists."}}]}, """
    """"sessionId": "session_plan_test3", "timestamp": "2025-11-23T08:00:00.000Z"}"""
)

# Expected plan text from JSONL_ASSISTANT_EXIT_PLAN_MODE
EXPECTED_PLAN_TEXT = """## Fix Session Plan Extraction

**Problem:** Path construction doesn't handle dots.

**Solution:** Convert dots to hyphens.

### Changes Required

1. Update path conversion logic
2. Add tests"""

# Expected plan text from JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER
EXPECTED_PLAN_TEXT_LATER = """## Updated Plan

**Problem:** This is the newer plan.

**Solution:** Should be returned when multiple plans exist."""


# Complete session file fixtures for integration testing

# Complete session with a plan
SESSION_WITH_PLAN = [
    JSONL_USER_MESSAGE_STRING,
    JSONL_ASSISTANT_TEXT,
    JSONL_ASSISTANT_EXIT_PLAN_MODE,
]

# Session with multiple plans at different timestamps
SESSION_MULTIPLE_PLANS = [
    JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER,
    JSONL_USER_MESSAGE_STRING,
    JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER,
]

# Session in agent subprocess file (should be included in search)
SESSION_AGENT_FILE_PLAN = [
    JSONL_USER_MESSAGE_STRING,
    JSONL_ASSISTANT_EXIT_PLAN_MODE,
]


def create_session_file(path, entries: list[str]) -> None:
    """Write JSONL entries to a session file.

    JSONL format requires each JSON object on a single line with no internal newlines.
    This function parses each entry and writes it as compact single-line JSON.

    Args:
        path: Path object or string path to write to
        entries: List of JSONL entry strings to write (can be pretty-printed)
    """
    import json
    from pathlib import Path

    file_path = Path(path)
    with open(file_path, "w", encoding="utf-8") as f:
        for entry in entries:
            # Parse JSON and write back as compact single-line
            data = json.loads(entry)
            f.write(json.dumps(data) + "\n")
