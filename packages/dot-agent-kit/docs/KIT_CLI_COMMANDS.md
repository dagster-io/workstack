# Kit CLI Commands

## Definition & Purpose

**Kit CLI commands** are Python scripts that handle mechanical git/gh/gt operations in isolated subprocess contexts, outputting structured JSON results. They exist as a **performance and cost-optimization pattern** for Claude Code interactions.

### Why Kit CLI Commands Exist

Traditional approach:

```
User → Claude → Multiple git/gh/gt commands in main context → Parse outputs
```

- Each command requires LLM orchestration (slow)
- Each command output pollutes main Claude context
- Token costs accumulate quickly
- Large outputs waste context space

Kit CLI command approach:

```
User → Claude → Single kit CLI command (subprocess) → JSON output
```

- **Performance**: Deterministic Python execution is much faster than LLM-based orchestration
- **Cost**: All mechanical operations run in isolated subprocess, dramatically reducing token usage
- **Determinism**: Known workflows execute reliably without AI overhead
- **Clarity**: Only final JSON result enters main Claude context
- **Maintainability**: Cleaner conversation flow and easier to test

## When to Use Kit CLI Commands

Create a kit CLI command when:

- **Performance and cost benefits**: Multiple git/gh/gt commands that can be executed deterministically (faster than LLM orchestration)
- **Workflow is repeatable**: The same sequence of operations will be used regularly
- **Structure is beneficial**: JSON output makes parsing and decision-making cleaner

Do NOT create a kit CLI command when:

- **Single operation**: One git command is sufficient
- **Highly variable**: Workflow changes significantly each time
- **Interactive required**: User input needed mid-workflow (use two-phase pattern instead)

## Architecture Patterns

Kit CLI commands follow two distinct patterns based on complexity:

### Single-Phase Pattern

**When to use**: Straightforward workflows without AI analysis between steps

**Canonical example**: [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/update_pr.py)

**Structure**:

1. Define Result/Error dataclasses
2. Implement helper functions (one per operation)
3. Implement execute function that orchestrates workflow
4. Add Click command wrapper
5. Output JSON

**Characteristics**:

- Linear workflow: Step 1 → Step 2 → Step 3 → Done
- All steps can be determined upfront
- No external input needed mid-workflow
- Single entry point

### Two-Phase Pattern

**When to use**: Complex workflows requiring AI analysis between mechanical steps

**Canonical example**: [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py)

**Structure**:

1. Define separate Result/Error dataclasses for each phase
2. Implement helper functions (shared across phases)
3. Implement `execute_pre_analysis()` function
4. Implement `execute_post_analysis()` function
5. Add Click group with subcommands for each phase
6. Output JSON from each phase

**Characteristics**:

- Pre-analysis: Gather context and prepare (squash commits, collect diffs)
- AI analysis: Claude analyzes results and generates content (commit messages, PR descriptions)
- Post-analysis: Apply AI-generated content and complete workflow
- Two entry points (subcommands)

**Why two phases?**

- AI analysis (slow, context-heavy, requires LLM) happens in main Claude context
- Mechanical operations (fast, deterministic, pure Python) happen in isolated subprocesses
- Clear separation of concerns

## Code Structure

### Canonical Examples

**Study these files to understand patterns - they are the authoritative implementations**:

- **Single-phase**: [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/update_pr.py) - Complete workflow example
- **Two-phase**: [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py) - Complex workflow with AI integration
- **Testing**: [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py) - Comprehensive test patterns

**IMPORTANT**: Follow these examples to avoid pattern drift. All patterns below are demonstrated in these files.

### Structure Overview

All kit CLI commands follow this organization:

1. **Comprehensive docstring**: Purpose, usage, exit codes, error types, examples
2. **Type definitions**: Error type literals using `Literal[]`
3. **Dataclasses**: Separate Result and Error classes with typed fields
4. **Helper functions**: One per operation, LBYL pattern, return `bool | str | None`
5. **Execute function**: Orchestrates workflow, returns Result or Error
6. **Click wrapper**: Command or group with JSON output

See [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/update_pr.py) for single-phase implementation and [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py) for two-phase implementation.

### Key Patterns

**Dataclasses**:

- Result: `success: bool` (always True), operation fields, context fields, human-readable `message`
- Error: `success: bool` (always False), `error_type: ErrorType` literal, `message: str`, `details: dict[str, str]`

See lines 47-66 in `update_pr.py` for examples.

**Helper Functions (LBYL)**:

- One function per operation
- Use `subprocess.run(..., check=False)` and check returncode explicitly
- Return simple types: `bool`, `str | None`, `tuple | None`
- Return `None` or `False` on failure, not exceptions

See lines 69-161 in `update_pr.py` for examples.

**Execute Function**:

- Orchestrates workflow by calling helpers in sequence
- Checks each result (LBYL)
- Returns Result on success, Error on failure
- Builds human-readable messages

See lines 163-234 in `update_pr.py` for single-phase example, lines 221-349 in `submit_branch.py` for two-phase example.

**Click Wrappers**:

- Single command (`@click.command()`) for single-phase
- Command group (`@click.group()`) with subcommands for two-phase
- JSON output via `click.echo(json.dumps(asdict(result), indent=2))`
- Exit with code 1 on error

See lines 237-256 in `update_pr.py` for single-phase, lines 352-417 in `submit_branch.py` for two-phase.

### JSON Output Format

All commands output JSON with `success` field and appropriate data/error fields. See canonical examples for complete structure.

## Registration

Kit CLI commands must be registered in the kit's `kit.yaml` file:

```yaml
name: my-kit
version: 0.1.0
description: Description of the kit
license: MIT
kit_cli_commands:
  - name: my-command
    path: kit_cli_commands/my-kit/my_command.py
    description: Brief description of what this command does
artifacts:
  command:
    - commands/my-kit/my-command.md
```

**Key points**:

- `name`: Command name (kebab-case)
- `path`: Relative path from kit root to Python file
- `description`: Brief description shown in help text
- Must be in `kit_cli_commands` section (not `artifacts`)

## Testing

**Follow the canonical testing pattern in [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py)** - it demonstrates all patterns below.

### Test Organization

Tests should have three classes:

1. **TestHelperFunctions**: Test each helper function (success and failure cases)
2. **TestExecuteCommand**: Test execute function workflow (success and all error types)
3. **TestCommandCLI**: Test Click command (JSON output, exit codes)

### Key Testing Patterns

- **Mock subprocess.run**: Use `unittest.mock.patch` and `subprocess.CompletedProcess`
- **Fixtures**: `runner: CliRunner` and `mock_subprocess: Mock`
- **Coverage**: Test success path and all error types
- **JSON validation**: Parse and verify structure in CLI tests
- **Exit codes**: Verify 0 for success, 1 for errors

See [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py) lines 25-593 for complete examples.

## Step-by-Step Workflow

### 1. Create Python File

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/kit_cli_commands/<kit-name>/my_command.py`

### 2. Implement Following Canonical Pattern

Study and follow the structure from [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/update_pr.py):

- Comprehensive docstring (lines 1-30)
- Error type literals (lines 39-44)
- Result/Error dataclasses (lines 47-66)
- Helper functions (lines 69-161)
- Execute function (lines 163-234)
- Click wrapper (lines 237-256)

For two-phase pattern, see [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py) lines 1-417.

### 3. Register in kit.yaml

Add entry to `kit_cli_commands` section (see Registration section above).

### 4. Create Slash Command

Create `.claude/commands/<kit>/<name>.md` to invoke the command and parse JSON response.

### 5. Write Tests

Follow [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py) pattern - three test classes covering helpers, execute function, and CLI.

### 6. Run Tests

```bash
uv run pytest tests/kits/<kit>/test_<name>.py
```

### 7. Verify Registration

```bash
uv run dot-agent run <kit> --help
```

## Common Patterns

Common helper function patterns are demonstrated in the canonical examples:

- **Git state checks**: `get_current_branch()`, `has_uncommitted_changes()` - see lines 69-112 in `update_pr.py`
- **GitHub PR operations**: `check_pr_exists()` - see lines 84-97 in `update_pr.py`
- **Git operations**: `stage_and_commit_changes()`, `restack_branch()`, `submit_updates()` - see lines 115-161 in `update_pr.py`
- **Graphite operations**: `get_parent_branch()`, `count_commits_in_branch()`, `squash_commits()` - see lines 127-169 in `submit_branch.py`

All follow the LBYL pattern: check returncode, return simple types, no exceptions.

## Best Practices

### Do

- **Follow canonical examples**: `update_pr.py` and `submit_branch.py` are authoritative
- **Use LBYL pattern**: Check conditions before acting
- **Return simple types from helpers**: `bool`, `str | None`, `tuple | None`
- **Use `check=False` in subprocess.run**: Handle errors explicitly
- **Provide comprehensive docstrings**: Purpose, usage, exit codes, error types, examples
- **Test all code paths**: Success and all error types
- **Use typed error literals**: `Literal["error_type_1", "error_type_2"]`

### Don't

- **Don't use exceptions for control flow**: Return None/False instead
- **Don't use `check=True` in subprocess.run**: Defeats the purpose of LBYL
- **Don't deviate from patterns**: Causes drift and maintenance issues
- **Don't skip docstrings**: Future maintainers need context
- **Don't skip tests**: Ensures reliability

## Relationship to Slash Commands

**Kit CLI commands** and **slash commands** work together:

- **Kit CLI command**: Handles mechanical operations, outputs JSON
- **Slash command**: Invokes kit CLI command, parses JSON, interprets for user

**Example flow**:

1. User runs: `/gt:update-pr`
2. Slash command invokes: `dot-agent run gt update-pr`
3. Kit CLI command executes git/gh/gt operations
4. Kit CLI command outputs JSON: `{"success": true, "pr_number": 123, ...}`
5. Slash command parses JSON and reports to user: "Successfully updated PR #123"

**Why this split?**

- **Performance and cost**: Deterministic operations execute in fast Python, stay out of slow LLM context
- **Reusability**: Kit CLI commands can be used by multiple slash commands
- **Testability**: Kit CLI commands can be tested independently
- **Clarity**: Clear separation between mechanical operations and AI interpretation

## Related Documentation

- [GLOSSARY.md](GLOSSARY.md) - Terminology and core concepts
- [DEVELOPING.md](../DEVELOPING.md) - Development workflow
