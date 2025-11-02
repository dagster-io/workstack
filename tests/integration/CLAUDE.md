# Integration Testing Patterns

## Purpose

Integration tests verify that abstraction layers correctly wrap external tools
(git, filesystem, shell). These tests use REAL implementations, not fakes.

## What Goes Here

- `test_real_gitops.py` - Tests RealGitOps with actual `git` subprocess calls
- `test_real_global_config.py` - Tests RealGlobalConfigOps with real filesystem I/O
- `test_dryrun_integration.py` - Tests dry-run wrappers intercept operations

## What DOESN'T Go Here

❌ Tests using fakes (FakeGitOps, etc.)
→ Go in `tests/commands/` or `tests/core/`

❌ Tests OF fakes themselves
→ Go in `tests/unit/fakes/`

## Key Characteristics

✅ Uses `tmp_path` pytest fixture for real directories
✅ Calls `subprocess.run()` with actual commands
✅ Performs real filesystem I/O
✅ Validates external tool integration

## Testing Pattern

```python
import subprocess
from pathlib import Path
import pytest

def test_real_gitops_with_actual_git(tmp_path: Path) -> None:
    """Test that RealGitOps correctly calls actual git command."""
    # Arrange: Set up real directory
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize real git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    git_ops = RealGitOps()

    # Act: Call git operation
    result = git_ops.list_branches(repo)

    # Assert: Verify real git behavior
    assert len(result) >= 1  # At least main/master branch exists
```

## When to Use tmp_path

Use the `tmp_path` pytest fixture for:

- Creating temporary directories
- Initializing real git repositories
- Writing actual config files
- Testing filesystem I/O

```python
def test_real_filesystem_io(tmp_path: Path) -> None:
    config_ops = RealGlobalConfigOps()

    # Write real config file
    config_file = tmp_path / "config.toml"
    config_file.write_text("[workstack]\nroot = /tmp/ws\n")

    # Load and verify
    config = config_ops.load_from_path(config_file)
    assert config.root == Path("/tmp/ws")
```

## See Also

- `tests/CLAUDE.md` - Overall test structure
- `docs/TESTING.md` - Complete testing guide
