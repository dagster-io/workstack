# CLI Command Testing Patterns

## Overview

All CLI command tests use dependency injection via WorkstackContext with fake implementations. Tests use Click's `CliRunner` to simulate command execution without actual filesystem or git operations.

## Subdirectory Organization

| Directory     | Focus                    | When to Load                           |
| ------------- | ------------------------ | -------------------------------------- |
| `workspace/`  | create, rename, rm, move | Workspace manipulation commands        |
| `navigation/` | switch, up, down         | Branch navigation commands             |
| `display/`    | status, tree, list       | Information display commands           |
| `shell/`      | Shell integration        | Shell wrapper generation and utilities |
| `management/` | plan                     | Workspace planning commands            |
| `setup/`      | init, config, completion | Initial configuration commands         |

## Standard Test Pattern

```python
from click.testing import CliRunner
from workstack.commands.create import create
from workstack.context import WorkstackContext
from tests.fakes.fake_gitops import FakeGitOps

def test_command_behavior() -> None:
    # Arrange: Set up fakes with desired state
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    ctx = WorkstackContext(
        git_ops=git_ops,
        # ... other dependencies
    )

    runner = CliRunner()

    # Act: Execute command
    result = runner.invoke(
        create,
        ["new-branch"],
        obj=ctx
    )

    # Assert: Verify behavior
    assert result.exit_code == 0
    assert "Created workspace" in result.output
    assert "new-branch" in git_ops.created_branches
```

## Context Construction

🔴 **CRITICAL: Use `env.build_context()` helper instead of manual construction**

The `simulated_workstack_env()` context manager provides an `env.build_context()` helper method that eliminates boilerplate when constructing `WorkstackContext` for tests.

### Anti-Pattern (DO NOT USE)

```python
# ❌ WRONG - Manual GlobalConfig construction with 5+ parameters
from workstack.core.global_config import GlobalConfig
from workstack.core.context import WorkstackContext

git_ops = FakeGitOps(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
)

global_config = GlobalConfig(
    workstacks_root=env.workstacks_root,
    use_graphite=False,
    shell_setup_complete=False,
    show_pr_info=True,
    show_pr_checks=False,
)

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config,
    script_writer=env.script_writer,
    cwd=env.cwd,
)
```

### Correct Pattern (USE THIS)

```python
# ✅ CORRECT - Use env.build_context() helper
git_ops = FakeGitOps(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
)

test_ctx = env.build_context(git_ops=git_ops)
```

### When to Override Defaults

The `env.build_context()` method accepts optional parameters to customize the context:

```python
# Override specific ops implementations
test_ctx = env.build_context(
    git_ops=custom_git_ops,
    graphite_ops=custom_graphite_ops,
    github_ops=FakeGitHubOps(),
)

# Enable Graphite integration
test_ctx = env.build_context(
    use_graphite=True,
    show_pr_checks=True,
)

# Combine custom ops with config flags
test_ctx = env.build_context(
    git_ops=git_ops,
    graphite_ops=graphite_ops,
    use_graphite=True,
    dry_run=False,
)
```

### Available Parameters

- `git_ops`: Custom GitOps implementation (defaults to FakeGitOps)
- `graphite_ops`: Custom GraphiteOps implementation (defaults to FakeGraphiteOps)
- `github_ops`: Custom GitHubOps implementation (defaults to FakeGitHubOps)
- `shell_ops`: Custom ShellOps implementation
- `script_writer`: Custom ScriptWriter implementation
- `use_graphite`: Enable Graphite integration (default: False)
- `show_pr_info`: Show PR information (default: True)
- `show_pr_checks`: Show PR checks (default: False)
- `dry_run`: Enable dry-run mode (default: False)
- `cwd`: Override current working directory (default: env.cwd)

### Why This Matters

Using `env.build_context()`:

1. **Reduces boilerplate**: Eliminates 10-15 lines of manual construction
2. **Prevents errors**: Automatically handles parameter wiring
3. **Improves maintainability**: Changes to GlobalConfig don't break every test
4. **Standardizes patterns**: All tests use consistent context construction

## Common Assertions

### Exit Codes

```python
# Success
assert result.exit_code == 0

# User error (validation, missing args)
assert result.exit_code == 2

# Runtime error (git failure, filesystem issue)
assert result.exit_code == 1
```

### Output Verification

```python
# Check for expected messages
assert "Success message" in result.output
assert "Expected value" in result.output

# Check error messages
assert result.exit_code != 0
assert "Error: Expected error" in result.output
```

### State Changes

```python
# Verify mutations via fake's read-only properties
assert "branch-name" in git_ops.created_branches
assert "old-name" in git_ops.deleted_branches
assert git_ops.rename_history == [("old", "new")]
```

## Testing CLI Options

### Boolean Flags

```python
result = runner.invoke(command, ["--force", "arg"])
```

### Options with Values

```python
result = runner.invoke(command, ["--option", "value", "arg"])
```

### Multiple Arguments

```python
result = runner.invoke(command, ["arg1", "arg2"])
```

## Error Handling Tests

```python
def test_command_with_invalid_input() -> None:
    # Arrange: Set up state that will cause validation error
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "existing-branch"]
    )

    ctx = WorkstackContext(git_ops=git_ops)
    runner = CliRunner()

    # Act: Try to create duplicate branch
    result = runner.invoke(create, ["existing-branch"], obj=ctx)

    # Assert: Verify error handling
    assert result.exit_code != 0
    assert "already exists" in result.output
```

## Subprocess Interaction

Commands that use `subprocess.run` should inject `FakeShellOps`:

```python
from tests.fakes.fake_shell_ops import FakeShellOps

shell_ops = FakeShellOps()
shell_ops.add_command_result(
    "git status",
    returncode=0,
    stdout="clean working tree"
)

ctx = WorkstackContext(shell_ops=shell_ops)
```

## See Also

- [../../docs/TESTING.md#unit-test-pattern](../../docs/TESTING.md#unit-test-pattern)
- [../CLAUDE.md](../CLAUDE.md) - Overview of test structure
- [../fakes/](../fakes/) - Available fake implementations
