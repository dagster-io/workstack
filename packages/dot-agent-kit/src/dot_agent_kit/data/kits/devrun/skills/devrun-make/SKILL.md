---
name: devrun-make
description: GNU Make build automation patterns, Makefile targets, and output parsing guidance for project build and maintenance tasks.
__dot_agent:
  kit_id: devrun
  kit_version: 0.1.0
  artifact_type: skill
  artifact_path: skills/devrun-make/SKILL.md
---

# make Skill

Comprehensive guide for executing make commands and parsing build automation results.

## Command Patterns

### Basic Invocations

```bash
# Run default target
make

# Run specific target
make test

# Run multiple targets
make clean build test

# Show available targets
make help

# Dry run (show what would execute)
make -n target

# Keep going on errors
make -k

# Run with specific number of jobs
make -j4
```

### Common Make Flags

**Execution:**

- `-n, --dry-run` - Print commands without executing
- `-k, --keep-going` - Continue despite errors
- `-j [N], --jobs[=N]` - Run N jobs in parallel
- `-B, --always-make` - Rebuild all targets unconditionally

**Output:**

- `-s, --silent` - Silent mode (don't print commands)
- `--debug[=FLAGS]` - Debug mode
- `--trace` - Print tracing information

**Directory:**

- `-C DIR, --directory=DIR` - Change to DIR before reading makefiles

**Other:**

- `-f FILE, --file=FILE` - Use FILE as makefile
- `-i, --ignore-errors` - Ignore errors from recipes
- `--warn-undefined-variables` - Warn on undefined variables

## Common Make Targets (Project-Specific)

These are typical targets found in Python projects:

### Testing

```bash
make test          # Run test suite
make test-verbose  # Run tests with verbose output
make test-coverage # Run tests with coverage report
make test-watch    # Run tests in watch mode
```

### Code Quality

```bash
make lint          # Run linter
make format        # Format code
make typecheck     # Run type checker
make check         # Run all quality checks
```

### Build

```bash
make build         # Build the project
make clean         # Clean build artifacts
make install       # Install dependencies
make dist          # Create distribution package
```

### CI/CD

```bash
make all-ci        # Run all CI checks
make pre-commit    # Run pre-commit checks
```

### Prettier (in this project)

```bash
make prettier         # Format all files with prettier
make prettier-check   # Check prettier formatting
```

## Output Parsing Patterns

### Successful Target Execution

```
make test
pytest tests/
============================= test session starts ==============================
collected 47 items

tests/test_config.py ....                                                [ 8%]
tests/test_paths.py ............                                        [ 34%]
============================== 47 passed in 3.21s ==============================
```

**Extract:**

- Target executed: `test`
- Underlying command: `pytest tests/`
- Command output (parse based on underlying tool)
- Success indicator from underlying tool

### Failed Target Execution

```
make build
python setup.py build
error: command 'gcc' failed with exit status 1
make: *** [build] Error 1
```

**Extract:**

- Target: `build`
- Command that failed: `python setup.py build`
- Error message: `command 'gcc' failed with exit status 1`
- Make error: `*** [build] Error 1`

### Multiple Targets

```
make clean build test
rm -rf build/ dist/ *.egg-info
python -m build
Successfully built package.tar.gz and package.whl
pytest tests/
============================== 47 passed in 3.21s ==============================
```

**Extract:**

- Multiple targets executed sequentially
- Each command's output
- Overall success

### Target Not Found

```
make invalid-target
make: *** No rule to make target 'invalid-target'.  Stop.
```

**Extract:**

- Invalid target: `invalid-target`
- Error: No rule found

### Missing Makefile

```
make: *** No targets specified and no makefile found.  Stop.
```

**Extract:**

- No Makefile in current directory
- Cannot execute any targets

## Parsing Strategy

### 1. Check Exit Code

- `0` = Target succeeded
- `1` = Command in recipe failed
- `2` = Make error (syntax, missing target, etc.)

### 2. Identify Target(s)

Extract target name(s) from command:

```bash
make test        # Target: test
make clean build # Targets: clean, build
```

### 3. Parse Recipe Output

Make executes shell commands. Parse output based on the underlying command:

- **pytest**: Use pytest parsing patterns
- **pyright**: Use pyright parsing patterns
- **ruff**: Use ruff parsing patterns
- **prettier**: Use prettier parsing patterns
- **Custom scripts**: Parse as appropriate

### 4. Identify Failure Point

If make reports error:

```
make: *** [target] Error N
```

Extract:

- **Failed target**: `target`
- **Exit code**: `N`
- **Command output**: Above the make error line

### 5. Distinguish Make Errors from Command Errors

**Make error** (syntax, missing target):

```
make: *** No rule to make target 'foo'.  Stop.
```

**Command error** (recipe command failed):

```
pytest tests/
... pytest output ...
make: *** [test] Error 1
```

## Common Scenarios

### Target Succeeds

**Summary**: "Executed 'make <target>'. <Summary of underlying command>. <Key metrics>. No errors detected."

**Example**:
"Executed 'make test'. All 47 tests passed in 3.21s. No errors detected."

### Target Fails

**Summary**: "Executed 'make <target>'. <What failed>. ERROR: <Error message>. <Location if available>. <Likely cause>."

**Example**:
"Executed 'make typecheck'. Type checking failed. ERROR: Type 'str' cannot be assigned to type 'int' at src/config.py:42. Likely cause: incorrect return type annotation."

### Make Error (No Target)

**Summary**: "Failed to execute make: <error message>"

**Example**:
"Failed to execute make: No rule to make target 'invalid-target'."

### Missing Makefile

**Summary**: "Failed to execute make: No makefile found"

## Error Reporting Requirements

When a make command fails, include:

1. **The target** that was executed
2. **The command** that failed (from recipe)
3. **Complete error message** from underlying command
4. **File and line number** if available
5. **Root cause assessment** based on error
6. **Enough context** for parent to fix without re-running

## Target-Specific Patterns

### make all-ci

This target typically runs multiple checks:

```bash
make all-ci
# Runs: lint, typecheck, test, format-check, etc.
```

Parse each sub-command's output and aggregate results.

### make lint

Typically runs ruff or similar:

```bash
make lint
ruff check src/
```

Use ruff parsing patterns.

### make typecheck

Typically runs pyright or mypy:

```bash
make typecheck
pyright src/
```

Use pyright parsing patterns.

### make test

Typically runs pytest:

```bash
make test
pytest tests/
```

Use pytest parsing patterns.

### make prettier / make prettier-check

Runs prettier:

```bash
make prettier
prettier --write .
```

Use prettier parsing patterns.

## Best Practices

1. **Check exit code first** - distinguishes success from failure
2. **Identify the target** - essential context
3. **Parse underlying command output** - use tool-specific patterns
4. **Provide complete error context** - parent needs full details
5. **Distinguish make errors from command errors**
6. **Keep successes brief** - focus on results
7. **Detail failures thoroughly** - include all diagnostic info
8. **Aggregate multi-target results** - summarize overall status

## Integration with runner Agent

The `runner` agent will:

1. Load this skill
2. Execute make command via Bash
3. Use these patterns to parse output
4. Use tool-specific skills for underlying commands (pytest, ruff, etc.)
5. Report structured results to parent agent

**Your job**: Provide this knowledge so the runner can correctly interpret make output and delegate to tool-specific skills as needed.

## Recursive Skill Loading

When make executes a tool command:

1. Runner detects the underlying tool (pytest, ruff, etc.)
2. Runner loads that tool's skill
3. Runner parses output using tool-specific patterns
4. Runner reports aggregate result

**Example**:

```
make test
  → executes: pytest tests/
  → runner loads pytest skill
  → runner parses pytest output
  → runner reports: "Executed 'make test'. All 47 tests passed."
```

## Example Outputs to Parse

### Example 1: Successful make test

```bash
$ make test
pytest tests/
============================== 47 passed in 3.21s ==============================
```

**Parse as**: make test succeeded, 47 tests passed

### Example 2: Failed make lint

```bash
$ make lint
ruff check src/
src/module.py:42:15: F841 Local variable `x` assigned but never used
Found 1 error.
make: *** [lint] Error 1
```

**Parse as**: make lint failed, 1 ruff violation found

### Example 3: Make error

```bash
$ make invalid
make: *** No rule to make target 'invalid'.  Stop.
```

**Parse as**: make error, target 'invalid' not found

### Example 4: make all-ci

```bash
$ make all-ci
ruff check src/
All checks passed!
pyright src/
0 errors, 0 warnings, 0 informations
pytest tests/
============================== 47 passed in 3.21s ==============================
```

**Parse as**: make all-ci succeeded, all checks passed (lint, typecheck, tests)
