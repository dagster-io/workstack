# Kit CLI Push Down Pattern

**Pattern Category**: Agent Architecture

**Use When**: Agent markdown or slash commands need mechanical data processing, validation, or transformation before LLM inference.

**Analogy**: Like database query optimizers that "push down" predicates closer to the data layer for efficiency, this pattern pushes computation from LLM prompts down to Python CLI commands where it's more efficient and reliable.

## Problem

Agent markdown files often contain bash code for mechanical computation tasks like:

- Parsing and validating input formats (URLs, numbers, paths)
- Extracting structured data from text
- Transforming data between formats
- Running deterministic computations

**Issues with bash in markdown**:

- Hard to test (no unit test framework)
- Requires permission approvals for execution
- Error-prone (regex varies by shell, no type safety)
- Increases token usage (bash code + error handling in prompt)
- Not reusable across agents

## Solution

**Push mechanical computation down to kit CLI commands written in Python.**

Kit CLI commands are standalone Python scripts that:

- Execute deterministic operations before LLM inference
- Return structured JSON output
- Are fully testable with unit tests
- Run without permission prompts (if allowlisted)
- Reduce token usage in agent prompts

## When to Use

Use kit CLI push down when code performs:

✅ **Parsing/Validation**

- URL parsing (extract issue numbers, repo info)
- Input format validation (number, enum, pattern matching)
- Path encoding/decoding

✅ **Data Extraction**

- Extracting fields from JSON/YAML/TOML
- Filtering and transforming structured data
- Computing derived values (hashes, checksums)

✅ **Deterministic Operations**

- File system queries (find directories, list files)
- String transformations (slugify, sanitize)
- Mathematical computations

✅ **Token Reduction**

- Compressing verbose data (session logs → XML summary)
- Pre-filtering large datasets
- Aggregating information from multiple sources

## When NOT to Use

❌ **Semantic Analysis**

- Summarizing text content
- Generating names or descriptions
- Making subjective decisions
- Understanding user intent

❌ **Content Generation**

- Writing commit messages
- Creating documentation
- Drafting responses
- Generating code

❌ **Complex Reasoning**

- Deciding "should I do X or Y?"
- Interpreting ambiguous requirements
- Making trade-off decisions
- Planning implementation steps

**Guideline**: If it requires understanding **meaning**, use LLM. If it's **mechanical transformation**, use kit CLI.

## Example: Issue Reference Parsing

### Before (Bash in Agent Markdown)

**Problems**:

- Bash regex fragile across shells
- No unit tests
- Permission prompt required
- Error handling verbose

**Agent markdown code**:

```bash
# Parse issue number from input
issue_arg="$1"
if [[ "$issue_arg" =~ github\.com/[^/]+/[^/]+/issues/([0-9]+) ]]; then
    issue_number="${BASH_REMATCH[1]}"
elif [[ "$issue_arg" =~ ^[0-9]+$ ]]; then
    issue_number="$issue_arg"
else
    echo "Error: Invalid input format"
    exit 1
fi
```

### After (Kit CLI Command)

**Benefits**:

- Robust Python regex
- 24 unit tests
- No permission prompt
- Structured JSON errors

**Agent markdown invocation**:

```bash
# Parse issue reference using kit CLI
parse_result=$(dot-agent run erk parse-issue-reference "$issue_arg")

# Check success
if ! echo "$parse_result" | jq -e '.success' > /dev/null; then
    error_msg=$(echo "$parse_result" | jq -r '.message')
    echo "Error: $error_msg"
    exit 1
fi

# Extract issue number
issue_number=$(echo "$parse_result" | jq -r '.issue_number')
```

**Kit CLI command** (`parse_issue_reference.py`):

```python
def parse_issue_reference(reference: str) -> ParsedIssue | ParseError:
    """Parse GitHub issue reference from plain number or URL."""
    # Try plain number
    if reference.isdigit():
        issue_number = int(reference)
        if issue_number <= 0:
            return ParseError(
                success=False,
                error="invalid_number",
                message=f"Issue number must be positive (got {issue_number})",
            )
        return ParsedIssue(success=True, issue_number=issue_number)

    # Try GitHub URL
    url_pattern = r"^https?://github\.com/[^/]+/[^/]+/issues/(\d+)(?:[?#].*)?$"
    match = re.match(url_pattern, reference)
    if match:
        issue_number = int(match.group(1))
        if issue_number <= 0:
            return ParseError(...)
        return ParsedIssue(success=True, issue_number=issue_number)

    # Neither format matched
    return ParseError(
        success=False,
        error="invalid_format",
        message="Issue reference must be a number or GitHub URL",
    )
```

## Implementation Checklist

When creating a kit CLI push down command:

1. **Create command file**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit}/kit_cli_commands/{kit}/{command}.py`
2. **Use dataclasses for output**: Success and error types with structured fields
3. **Return JSON**: Use `json.dumps(asdict(result))` for consistent output
4. **Write unit tests**: Test success cases, edge cases, and error handling
5. **Register in kit.yaml**: Add entry under `kit_cli_commands`
6. **Update agent markdown**: Replace bash logic with kit CLI invocation
7. **Parse JSON in agent**: Use `jq` to extract fields and check `success`

## Benefits

✅ **Testability**: Unit tests with pytest, full coverage
✅ **Reliability**: Python type safety, robust error handling
✅ **Performance**: No permission prompts, faster execution
✅ **Reusability**: Command usable across multiple agents
✅ **Token Efficiency**: Reduces prompt size, cleaner agent logic
✅ **Maintainability**: Standard Python code, easy to refactor

## Anti-Patterns

❌ **Using kit CLI for semantic tasks**: Don't push content generation or decision-making to Python

❌ **Complex business logic in commands**: Keep commands simple - complex orchestration belongs in agent

❌ **Tight coupling to single agent**: Design commands to be reusable

❌ **Returning unstructured output**: Always use structured JSON with success indicators

## Related Patterns

- **Agent Delegation**: Kit CLI handles pushed-down computation, agent handles orchestration
- **Structured Output**: Dataclasses ensure consistent JSON schemas
- **Error Boundaries**: Kit CLI returns errors as data, not exceptions

## References

- Implementation: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/parse_issue_reference.py`
- Tests: `packages/dot-agent-kit/tests/unit/kits/erk/test_parse_issue_reference.py`
- Usage: `.claude/agents/erk/issue-wt-creator.md`
- Kit CLI Documentation: `docs/agent/kit-cli-commands.md`
