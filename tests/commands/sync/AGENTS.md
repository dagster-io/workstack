# Sync Command Testing Patterns

## Overview

Tests for the `erk sync` command, which synchronizes Graphite stacks
and manages worktree navigation.

## Command Responsibilities

The sync command:

1. Requires Graphite to be enabled
2. Runs `gt sync` from root worktree
3. Returns user to current worktree after sync
4. Handles shell integration for directory changes

## Test Pattern

```python
from click.testing import CliRunner
from tests.fakes.fake_git import FakeGit
from tests.fakes.fake_config_store import FakeConfigStore
from tests.fakes.fake_graphite import FakeGraphite
from erk.cli.cli import cli
from erk.core.context import ErkContext

def test_sync_command() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup
        cwd = Path.cwd()
        git = FakeGit(git_common_dirs={cwd: cwd / ".git"})
        config_store = FakeConfigStore(use_graphite=True, ...)

        ctx = ErkContext(
            git=git,
            config_store=config_store,
            graphite=FakeGraphite(),
            # ...
        )

        # Act
        result = runner.invoke(cli, ["sync"], obj=ctx)

        # Assert
        assert result.exit_code == 0
```

## Why isolated_filesystem?

Sync command may check for worktree directory existence or write temp files
for shell integration. The `isolated_filesystem()` provides a clean test
environment.

## See Also

- `tests/commands/CLAUDE.md` - General command testing patterns
- `docs/TESTING.md` - Complete testing guide
