# Shell Integration Testing Patterns

## Overview

This directory contains tests for shell integration features, including shell wrapper generation, CWD (current working directory) recovery, and shell utilities.

## Test Files in This Directory

- `test_shell_integration.py` - Shell wrapper generation and integration
- `test_shell_wrappers.py` - Shell-specific wrapper code
- `test_prepare_cwd_recovery.py` - CWD state preservation
- `test_shell_utils.py` - Shell utility functions

## Shell Integration Overview

Workstack integrates with shells (bash, zsh, fish) to provide:

1. Command wrappers that preserve shell state
2. Working directory recovery after commands
3. Shell-specific syntax generation

## Testing Shell Wrapper Generation

Shell wrappers allow workstack commands to affect the parent shell:

```python
from workstack.commands.shell import prepare_shell_integration

def test_shell_wrapper_generation() -> None:
    shell_ops = FakeShellOps()

    ctx = WorkstackContext(shell_ops=shell_ops)
    runner = CliRunner()

    result = runner.invoke(prepare_shell_integration, ["bash"], obj=ctx)

    assert result.exit_code == 0
    assert "function workstack" in result.output or "workstack()" in result.output
```

## Testing Different Shell Types

### Bash/Zsh

```python
def test_bash_wrapper() -> None:
    result = runner.invoke(prepare_shell_integration, ["bash"], obj=ctx)

    assert result.exit_code == 0
    # Check for bash-specific syntax
    assert "function" in result.output or "()" in result.output
```

### Fish

```python
def test_fish_wrapper() -> None:
    result = runner.invoke(prepare_shell_integration, ["fish"], obj=ctx)

    assert result.exit_code == 0
    # Check for fish-specific syntax
    assert "function workstack" in result.output
```

## CWD Recovery Testing

Commands that change directories need to restore CWD:

```python
def test_cwd_recovery() -> None:
    from workstack.shell.cwd_recovery import prepare_cwd_recovery

    initial_cwd = "/initial/path"
    target_cwd = "/target/path"

    shell_ops = FakeShellOps()
    git_ops = FakeGitOps(current_branch="main")

    ctx = WorkstackContext(
        shell_ops=shell_ops,
        git_ops=git_ops,
        cwd=initial_cwd
    )

    # Command changes to target directory
    result = runner.invoke(switch, ["other-branch"], obj=ctx)

    assert result.exit_code == 0
    # Verify CWD recovery commands were generated
    assert f"cd {target_cwd}" in shell_ops.generated_output
```

## FakeShellOps Usage Patterns

The `FakeShellOps` fake tracks shell operations:

```python
from tests.fakes.fake_shell_ops import FakeShellOps

def test_shell_command_execution() -> None:
    shell_ops = FakeShellOps()

    # Pre-configure command results
    shell_ops.add_command_result(
        "git status",
        returncode=0,
        stdout="On branch main\nnothing to commit"
    )

    ctx = WorkstackContext(shell_ops=shell_ops)

    # Execute command that runs subprocess
    result = runner.invoke(status, [], obj=ctx)

    # Verify subprocess was called
    assert "git status" in shell_ops.executed_commands
```

## Testing Subprocess Interaction

Commands may execute git or other subprocess commands:

```python
def test_subprocess_calls() -> None:
    shell_ops = FakeShellOps()

    # Configure expected subprocess result
    shell_ops.add_command_result(
        "git branch --show-current",
        returncode=0,
        stdout="main\n"
    )

    ctx = WorkstackContext(shell_ops=shell_ops)
    runner = CliRunner()

    result = runner.invoke(status, [], obj=ctx)

    assert result.exit_code == 0
    # Verify command was executed
    assert any("git branch" in cmd for cmd in shell_ops.executed_commands)
```

## Shell Output Capture

Testing commands that capture and process shell output:

```python
def test_shell_output_processing() -> None:
    shell_ops = FakeShellOps()

    # Multi-line output
    shell_ops.add_command_result(
        "git branch -a",
        returncode=0,
        stdout="  main\n* feature/test\n  feature/other\n"
    )

    ctx = WorkstackContext(shell_ops=shell_ops)

    # Command processes branch list
    result = runner.invoke(list_cmd, [], obj=ctx)

    assert result.exit_code == 0
    assert "feature/test" in result.output
```

## Error Handling

Testing shell command failures:

```python
def test_shell_command_failure() -> None:
    shell_ops = FakeShellOps()

    # Simulate git command failure
    shell_ops.add_command_result(
        "git status",
        returncode=128,
        stderr="fatal: not a git repository"
    )

    ctx = WorkstackContext(shell_ops=shell_ops)
    runner = CliRunner()

    result = runner.invoke(status, [], obj=ctx)

    # Command should handle error gracefully
    assert result.exit_code != 0
    assert "not a git repository" in result.output
```

## Testing Shell-Specific Behavior

### Environment Variables

```python
def test_shell_environment() -> None:
    shell_ops = FakeShellOps()
    shell_ops.set_env("WORKSTACK_HOME", "/custom/path")

    ctx = WorkstackContext(shell_ops=shell_ops)

    # Command should respect environment
    result = runner.invoke(init, [], obj=ctx)

    assert "/custom/path" in result.output
```

### Shell Aliases

```python
def test_shell_alias_generation() -> None:
    result = runner.invoke(
        prepare_shell_integration,
        ["--alias", "ws"],
        obj=ctx
    )

    assert result.exit_code == 0
    assert "alias ws=" in result.output or "ws()" in result.output
```

## Integration with Other Commands

Shell operations often accompany other operations:

```python
def test_command_with_shell_wrapper() -> None:
    git_ops = FakeGitOps(
        current_branch="main",
        all_branches=["main", "feature"]
    )
    shell_ops = FakeShellOps()

    ctx = WorkstackContext(
        git_ops=git_ops,
        shell_ops=shell_ops,
        cwd="/workspace"
    )

    # Command that switches branch and changes directory
    result = runner.invoke(switch, ["feature"], obj=ctx)

    assert result.exit_code == 0
    # Verify both git and shell operations
    assert "feature" in git_ops.checked_out_branches
    assert any("cd" in cmd for cmd in shell_ops.generated_output)
```

## See Also

- [../CLAUDE.md](../CLAUDE.md) - General CLI command patterns
- [../../fakes/fake_shell_ops.py](../../fakes/fake_shell_ops.py) - FakeShellOps implementation
- [../../docs/TESTING.md](../../../docs/TESTING.md) - Complete testing guide
