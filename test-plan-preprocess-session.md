# Test Plan: Session Log Preprocessor

## Overview

Comprehensive test suite for `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/preprocess_session.py`

**Status**: Fixtures created, tests pending implementation

**Location**: `packages/dot-agent-kit/tests/unit/kits/erk/test_preprocess_session.py`

## Test File Structure

```
packages/dot-agent-kit/tests/unit/kits/erk/
├── __init__.py                    ✅ Created
├── fixtures.py                    ✅ Created (real session data)
└── test_preprocess_session.py     ⏳ Pending
```

## Module Under Test

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/preprocess_session.py`

**Functions to test**:

1. `escape_xml(text: str) -> str` - XML special character escaping
2. `deduplicate_assistant_messages(entries: list[dict]) -> list[dict]` - Remove duplicate assistant text
3. `generate_compressed_xml(entries: list[dict], source_label: str | None) -> str` - Generate XML output
4. `process_log_file(log_path: Path, source_label: str | None) -> list[dict]` - Parse JSONL file
5. `discover_agent_logs(session_log_path: Path) -> list[Path]` - Find agent-\*.jsonl files
6. `preprocess_session(log_path: Path, include_agents: bool) -> None` - Main CLI command

## Test Coverage Plan

### 1. XML Escaping Tests (4 tests)

**Function**: `escape_xml(text: str) -> str`

```python
def test_escape_xml_basic():
    """Test escaping of basic special characters."""
    assert escape_xml("a < b") == "a &lt; b"
    assert escape_xml("a > b") == "a &gt; b"
    assert escape_xml("a & b") == "a &amp; b"

def test_escape_xml_all_special_chars():
    """Test escaping all special characters together."""
    assert escape_xml("<tag>&content</tag>") == "&lt;tag&gt;&amp;content&lt;/tag&gt;"

def test_escape_xml_no_special_chars():
    """Test that normal text passes through unchanged."""
    assert escape_xml("hello world") == "hello world"
    assert escape_xml("foo-bar_baz123") == "foo-bar_baz123"

def test_escape_xml_empty_string():
    """Test that empty string returns empty string."""
    assert escape_xml("") == ""
```

**Rationale**: XML escaping is critical - incorrect escaping breaks XML parsing and could expose vulnerabilities.

---

### 2. Assistant Message Deduplication Tests (5 tests)

**Function**: `deduplicate_assistant_messages(entries: list[dict]) -> list[dict]`

**Pattern being tested**: When assistant messages arrive incrementally (text, then text+tool_use), the duplicate text should be dropped when tool_use is present.

```python
def test_deduplicate_removes_duplicate_text_with_tool_use():
    """Test that duplicate assistant text is removed when tool_use present."""
    # Setup: Two assistant messages with same text, second has tool_use
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll help"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "I'll help"},
            {"type": "tool_use", "id": "toolu_123", "name": "Read"}
        ]}}
    ]
    result = deduplicate_assistant_messages(entries)

    # First message unchanged, second message should only have tool_use
    assert len(result[1]["message"]["content"]) == 1
    assert result[1]["message"]["content"][0]["type"] == "tool_use"

def test_deduplicate_preserves_text_without_tool_use():
    """Test that text is preserved when no tool_use present."""
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "First"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Second"}]}}
    ]
    result = deduplicate_assistant_messages(entries)

    # Both messages should keep their text
    assert result[0]["message"]["content"][0]["text"] == "First"
    assert result[1]["message"]["content"][0]["text"] == "Second"

def test_deduplicate_preserves_first_assistant_text():
    """Test that first assistant message is never deduplicated."""
    entries = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}
    ]
    result = deduplicate_assistant_messages(entries)
    assert result[0]["message"]["content"][0]["text"] == "Hello"

def test_deduplicate_handles_empty_content():
    """Test handling of assistant messages with empty content."""
    entries = [
        {"type": "assistant", "message": {"content": []}}
    ]
    result = deduplicate_assistant_messages(entries)
    assert result == entries

def test_deduplicate_handles_no_assistant_messages():
    """Test handling of entries with no assistant messages."""
    entries = [
        {"type": "user", "message": {"content": "Hello"}}
    ]
    result = deduplicate_assistant_messages(entries)
    assert result == entries
```

**Rationale**: Deduplication is core to compression - must work correctly with incremental message patterns.

---

### 3. XML Generation Tests (8 tests)

**Function**: `generate_compressed_xml(entries: list[dict], source_label: str | None) -> str`

```python
def test_generate_xml_user_message_string_content():
    """Test XML generation for user message with string content."""
    from fixtures import JSONL_USER_MESSAGE_STRING, EXPECTED_XML_USER_STRING
    entries = [json.loads(JSONL_USER_MESSAGE_STRING)]
    xml = generate_compressed_xml(entries)
    assert EXPECTED_XML_USER_STRING in xml
    assert "<session>" in xml
    assert "</session>" in xml

def test_generate_xml_user_message_structured_content():
    """Test XML generation for user message with structured content."""
    from fixtures import JSONL_USER_MESSAGE_STRUCTURED, EXPECTED_XML_USER_STRUCTURED
    entries = [json.loads(JSONL_USER_MESSAGE_STRUCTURED)]
    xml = generate_compressed_xml(entries)
    assert EXPECTED_XML_USER_STRUCTURED in xml

def test_generate_xml_assistant_text():
    """Test XML generation for assistant text."""
    from fixtures import JSONL_ASSISTANT_TEXT, EXPECTED_XML_ASSISTANT_TEXT
    entries = [json.loads(JSONL_ASSISTANT_TEXT)]
    xml = generate_compressed_xml(entries)
    assert EXPECTED_XML_ASSISTANT_TEXT in xml

def test_generate_xml_assistant_tool_use():
    """Test XML generation for assistant with tool_use."""
    from fixtures import JSONL_ASSISTANT_TOOL_USE, EXPECTED_XML_TOOL_USE
    entries = [json.loads(JSONL_ASSISTANT_TOOL_USE)]
    xml = generate_compressed_xml(entries)
    assert '<tool_use name="Read" id="toolu_abc123">' in xml
    assert '<param name="file_path">/test/file.py</param>' in xml

def test_generate_xml_tool_result():
    """Test XML generation for tool results (preserves verbosity)."""
    from fixtures import JSONL_TOOL_RESULT
    entries = [json.loads(JSONL_TOOL_RESULT)]
    xml = generate_compressed_xml(entries)
    assert '<tool_result tool="toolu_abc123">' in xml
    assert "File contents:" in xml
    assert "def hello():" in xml  # Preserves formatting

def test_generate_xml_extracts_git_branch_metadata():
    """Test that git branch is extracted to metadata."""
    entries = [{"type": "user", "message": {"content": "test"}, "gitBranch": "test-branch"}]
    xml = generate_compressed_xml(entries)
    assert '<meta branch="test-branch" />' in xml

def test_generate_xml_includes_source_label():
    """Test that source label is included for agent logs."""
    entries = [{"type": "user", "message": {"content": "test"}}]
    xml = generate_compressed_xml(entries, source_label="agent-123")
    assert '<meta source="agent-123" />' in xml

def test_generate_xml_empty_entries():
    """Test handling of empty entries list."""
    xml = generate_compressed_xml([])
    assert xml == "<session>\n</session>"
```

**Rationale**: XML generation is the core output - must handle all entry types correctly and preserve tool result verbosity.

---

### 4. Log File Processing Tests (6 tests)

**Function**: `process_log_file(log_path: Path, source_label: str | None) -> list[dict]`

```python
def test_process_log_file_filters_file_history_snapshot(tmp_path: Path):
    """Test that file-history-snapshot entries are filtered out."""
    from fixtures import JSONL_FILE_HISTORY_SNAPSHOT, JSONL_USER_MESSAGE_STRING
    log_file = tmp_path / "test.jsonl"
    log_file.write_text(
        f"{JSONL_FILE_HISTORY_SNAPSHOT}\n{JSONL_USER_MESSAGE_STRING}",
        encoding="utf-8"
    )

    entries = process_log_file(log_file)
    assert len(entries) == 1  # Only user message, snapshot filtered
    assert entries[0]["type"] == "user"

def test_process_log_file_strips_metadata(tmp_path: Path):
    """Test that metadata fields are stripped."""
    from fixtures import JSONL_USER_MESSAGE_STRING
    log_file = tmp_path / "test.jsonl"
    log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

    entries = process_log_file(log_file)
    # Should NOT have metadata fields
    assert "parentUuid" not in entries[0]
    assert "sessionId" not in entries[0]
    assert "cwd" not in entries[0]
    assert "timestamp" not in entries[0]
    assert "userType" not in entries[0]
    assert "isSidechain" not in entries[0]

def test_process_log_file_removes_usage_field(tmp_path: Path):
    """Test that usage metadata is removed from assistant messages."""
    from fixtures import JSONL_ASSISTANT_TEXT
    log_file = tmp_path / "test.jsonl"
    log_file.write_text(JSONL_ASSISTANT_TEXT, encoding="utf-8")

    entries = process_log_file(log_file)
    assert "usage" not in entries[0]["message"]

def test_process_log_file_preserves_git_branch(tmp_path: Path):
    """Test that gitBranch is preserved for metadata extraction."""
    from fixtures import JSONL_USER_MESSAGE_STRING
    log_file = tmp_path / "test.jsonl"
    log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

    entries = process_log_file(log_file)
    assert entries[0]["gitBranch"] == "test-branch"

def test_process_log_file_handles_empty_file(tmp_path: Path):
    """Test handling of empty log file."""
    log_file = tmp_path / "empty.jsonl"
    log_file.write_text("", encoding="utf-8")

    entries = process_log_file(log_file)
    assert entries == []

def test_process_log_file_handles_malformed_json(tmp_path: Path):
    """Test handling of malformed JSON lines."""
    log_file = tmp_path / "malformed.jsonl"
    log_file.write_text("{invalid json}", encoding="utf-8")

    # Should raise JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        process_log_file(log_file)
```

**Rationale**: File processing is the input layer - must correctly filter, strip, and preserve data.

---

### 5. Agent Log Discovery Tests (4 tests)

**Function**: `discover_agent_logs(session_log_path: Path) -> list[Path]`

```python
def test_discover_agent_logs_finds_all(tmp_path: Path):
    """Test that all agent logs are discovered."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    agent1 = tmp_path / "agent-abc.jsonl"
    agent2 = tmp_path / "agent-def.jsonl"
    agent1.write_text("{}", encoding="utf-8")
    agent2.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log)
    assert len(agents) == 2
    assert agent1 in agents
    assert agent2 in agents

def test_discover_agent_logs_returns_sorted(tmp_path: Path):
    """Test that agent logs are returned in sorted order."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    agent_z = tmp_path / "agent-zzz.jsonl"
    agent_a = tmp_path / "agent-aaa.jsonl"
    agent_z.write_text("{}", encoding="utf-8")
    agent_a.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log)
    assert agents[0].name == "agent-aaa.jsonl"
    assert agents[1].name == "agent-zzz.jsonl"

def test_discover_agent_logs_ignores_other_files(tmp_path: Path):
    """Test that non-agent files are ignored."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    agent = tmp_path / "agent-abc.jsonl"
    other = tmp_path / "other-file.jsonl"
    agent.write_text("{}", encoding="utf-8")
    other.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log)
    assert len(agents) == 1
    assert agents[0] == agent

def test_discover_agent_logs_empty_directory(tmp_path: Path):
    """Test handling of directory with no agent logs."""
    session_log = tmp_path / "session-123.jsonl"
    session_log.write_text("{}", encoding="utf-8")

    agents = discover_agent_logs(session_log)
    assert agents == []
```

**Rationale**: Agent log discovery must correctly identify only agent logs, in sorted order.

---

### 6. CLI Command Tests (6 tests)

**Function**: `preprocess_session(log_path: Path, include_agents: bool) -> None`

**Uses**: `CliRunner` from Click for testing

```python
def test_preprocess_session_creates_temp_file(tmp_path: Path):
    """Test that command creates temp file."""
    from click.testing import CliRunner
    from fixtures import JSONL_USER_MESSAGE_STRING

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        # Extract temp file path from output
        temp_path = Path(result.output.strip())
        assert temp_path.exists()
        assert temp_path.name == "session-session-123-compressed.xml"

def test_preprocess_session_outputs_path(tmp_path: Path):
    """Test that command outputs temp file path to stdout."""
    from click.testing import CliRunner
    from fixtures import JSONL_USER_MESSAGE_STRING

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert "/tmp/session-session-123-compressed.xml" in result.output or \
               "/var/folders/" in result.output  # macOS temp dir

def test_preprocess_session_includes_agents_by_default(tmp_path: Path):
    """Test that agent logs are included by default."""
    from click.testing import CliRunner
    from fixtures import JSONL_USER_MESSAGE_STRING

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        agent_file = Path("agent-abc.jsonl")
        agent_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        # Check temp file contains multiple sessions
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert content.count("<session>") == 2  # Main + agent

def test_preprocess_session_no_include_agents_flag(tmp_path: Path):
    """Test --no-include-agents flag excludes agent logs."""
    from click.testing import CliRunner
    from fixtures import JSONL_USER_MESSAGE_STRING

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        agent_file = Path("agent-abc.jsonl")
        agent_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-include-agents"])
        assert result.exit_code == 0

        # Check temp file contains only main session
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert content.count("<session>") == 1  # Only main

def test_preprocess_session_nonexistent_file():
    """Test handling of nonexistent log file."""
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(preprocess_session, ["/nonexistent/file.jsonl"])
    assert result.exit_code != 0  # Should fail

def test_preprocess_session_agent_logs_with_source_labels(tmp_path: Path):
    """Test that agent logs include source labels."""
    from click.testing import CliRunner
    from fixtures import JSONL_USER_MESSAGE_STRING

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        agent_file = Path("agent-xyz.jsonl")
        agent_file.write_text(JSONL_USER_MESSAGE_STRING, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        # Check temp file has source labels
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert '<meta source="agent-xyz" />' in content
```

**Rationale**: CLI integration tests verify the command works end-to-end with Click framework.

---

### 7. Full Workflow Integration Tests (3 tests)

**Purpose**: Validate end-to-end behavior with realistic data

```python
def test_full_workflow_compression_ratio(tmp_path: Path):
    """Test that full workflow achieves expected compression ratio."""
    from click.testing import CliRunner

    # Create log file with realistic content (multiple entries with metadata)
    log_entries = [
        JSONL_USER_MESSAGE_STRING,
        JSONL_ASSISTANT_TEXT,
        JSONL_ASSISTANT_TOOL_USE,
        JSONL_TOOL_RESULT,
        JSONL_FILE_HISTORY_SNAPSHOT  # Should be filtered
    ]

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text("\n".join(log_entries), encoding="utf-8")

        original_size = log_file.stat().st_size

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        compressed_size = temp_path.stat().st_size

        compression_ratio = (1 - compressed_size / original_size) * 100
        assert compression_ratio >= 50  # Should achieve at least 50% compression

def test_full_workflow_preserves_tool_results(tmp_path: Path):
    """Test that tool results are preserved verbatim in full workflow."""
    from click.testing import CliRunner
    from fixtures import JSONL_TOOL_RESULT

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(JSONL_TOOL_RESULT, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")

        # Verify tool result content preserved with formatting
        assert "File contents:" in content
        assert "def hello():" in content
        assert "print('Hello')" in content

def test_full_workflow_deduplicates_correctly(tmp_path: Path):
    """Test that deduplication works correctly in full workflow."""
    from click.testing import CliRunner
    from fixtures import JSONL_DUPLICATE_ASSISTANT_TEXT, JSONL_DUPLICATE_ASSISTANT_WITH_TOOL

    runner = CliRunner()
    with runner.isolated_filesystem():
        log_file = Path("session-123.jsonl")
        log_file.write_text(
            f"{JSONL_DUPLICATE_ASSISTANT_TEXT}\n{JSONL_DUPLICATE_ASSISTANT_WITH_TOOL}",
            encoding="utf-8"
        )

        result = runner.invoke(preprocess_session, [str(log_file)])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")

        # First assistant should have text
        # Second assistant should only have tool_use (text deduplicated)
        assert content.count("I'll help you with that.") == 1  # Only once
        assert '<tool_use name="Edit"' in content  # Tool preserved
```

**Rationale**: Full workflow tests ensure all components work together correctly.

---

## Test Implementation Checklist

### Setup

- [x] Create test directory: `packages/dot-agent-kit/tests/unit/kits/erk/`
- [x] Create `__init__.py`
- [x] Create `fixtures.py` with real session data
- [ ] Create `test_preprocess_session.py`

### Test Categories

- [ ] XML Escaping (4 tests)
- [ ] Deduplication (5 tests)
- [ ] XML Generation (8 tests)
- [ ] Log Processing (6 tests)
- [ ] Agent Discovery (4 tests)
- [ ] CLI Command (6 tests)
- [ ] Full Workflow (3 tests)

### Validation

- [ ] Run tests: `pytest packages/dot-agent-kit/tests/unit/kits/erk/test_preprocess_session.py -v`
- [ ] Verify all 36 tests pass
- [ ] Check test coverage with `pytest --cov`
- [ ] Run CI checks: `make test-unit` (unit tests only)

## Success Criteria

✅ **Coverage**: All 7 functions have unit tests
✅ **Edge cases**: Empty inputs, malformed data, missing files tested
✅ **Real data**: Fixtures extracted from actual session logs
✅ **Integration**: CLI command tested with CliRunner
✅ **Compression**: Full workflow validates compression and preservation
✅ **Standards**: Tests follow dignified-python and fake-driven-testing patterns

## Implementation Notes

### Key Testing Patterns

1. **Pure functions first**: Test `escape_xml()` and `deduplicate_assistant_messages()` first (easiest)
2. **Use tmp_path for I/O**: All file operations use pytest's `tmp_path` fixture
3. **CliRunner for CLI**: Use Click's `CliRunner` with `isolated_filesystem()`
4. **Real data in fixtures**: All fixtures are real JSONL entries from actual session logs
5. **LBYL testing**: Check conditions explicitly in assertions

### Common Imports

```python
import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.preprocess_session import (
    escape_xml,
    deduplicate_assistant_messages,
    generate_compressed_xml,
    process_log_file,
    discover_agent_logs,
    preprocess_session,
)

from . import fixtures
```

### Example Test Template

```python
def test_function_behavior_description(tmp_path: Path):
    """Test that function does X when Y."""
    # Arrange
    setup_data = ...

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result == expected_value
    assert some_condition_holds
```

## Next Steps

1. Implement `test_preprocess_session.py` with all 36 tests
2. Run test suite and fix any failures
3. Add to CI pipeline (already covered by `make test-unit`)
4. Consider integration tests if subprocess interaction needed (currently unit-only)
