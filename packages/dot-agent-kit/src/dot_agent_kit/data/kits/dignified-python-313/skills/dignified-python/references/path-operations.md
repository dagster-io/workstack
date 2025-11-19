# Path Operations - Safe Pathlib Usage

## The Golden Rule

**ALWAYS check `.exists()` BEFORE `.resolve()` or `.is_relative_to()`**

## Why This Matters

- `.resolve()` raises `OSError` for non-existent paths
- `.is_relative_to()` raises `ValueError` for invalid comparisons
- Checking `.exists()` first avoids exceptions entirely

## Correct Patterns

```python
from pathlib import Path

# ✅ CORRECT: Check exists first
for wt_path in worktree_paths:
    if wt_path.exists():
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break

# ❌ WRONG: Using exceptions for path validation
try:
    wt_path_resolved = wt_path.resolve()
    if current_dir.is_relative_to(wt_path_resolved):
        current_worktree = wt_path_resolved
except (OSError, ValueError):
    continue
```

## Pathlib Best Practices

### Always Use Pathlib

```python
# ✅ CORRECT: Use pathlib.Path
from pathlib import Path

config_file = Path.home() / ".config" / "app.yml"
if config_file.exists():
    content = config_file.read_text(encoding="utf-8")

# ❌ WRONG: Use os.path
import os.path
config_file = os.path.join(os.path.expanduser("~"), ".config", "app.yml")
```

### Encoding Specification

```python
# ✅ CORRECT: Always specify encoding
content = path.read_text(encoding="utf-8")
path.write_text(data, encoding="utf-8")

# ❌ WRONG: Default encoding
content = path.read_text()  # Platform-dependent!
```

### Safe Directory Operations

```python
# ✅ CORRECT: Check before operations
def safe_mkdir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        raise ValueError(f"{path} exists but is not a directory")

# ✅ CORRECT: Parent validation
def write_file_safely(file_path: Path, content: str) -> None:
    parent = file_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
```

## Key Takeaways

1. **Check first**: Always `.exists()` before path operations
2. **Use pathlib**: Never `os.path` in new code
3. **Specify encoding**: Always use `encoding="utf-8"`
4. **Parent safety**: Ensure parent directories exist before writing
5. **LBYL principle**: Validate paths before operations, not in exception handlers
