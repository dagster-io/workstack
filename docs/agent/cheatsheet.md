# Workstack Cheat Sheet

**Purpose**: One-page quick reference for rules, patterns, and common mistakes

**When to use**: Before writing code, when debugging, or when stuck

---

## ⚡ Core Rules (DO This)

```python
# Exception Handling - LBYL (Look Before You Leap)
if key in dict:                       # ✅ Check first
    value = dict[key]
if path.exists():                     # ✅ Check exists before resolve
    path.resolve()

# Type Annotations - Modern Python 3.13+
list[str], dict[str, int], str | None # ✅ Lowercase built-ins

# Dependency Injection - ABC not Protocol
class MyOps(ABC):                     # ✅ Explicit interface
    @abstractmethod
    def method(self): ...

# Imports - Absolute only
from workstack.module import x        # ✅ Full path

# Dataclasses - Always frozen
@dataclass(frozen=True)               # ✅ Immutable
class Config: ...

# Code Style - Early returns
if not valid: return                  # ✅ Max 4 indent levels
```

---

## 🚫 Common Mistakes (DON'T Do This)

### Mistake #1: try/except for Control Flow 🔥 CRITICAL

```python
# ❌ WRONG - 90% of agent mistakes
try:
    value = mapping[key]
    process(value)
except KeyError:
    handle_missing()

# ✅ RIGHT - Use LBYL
if key in mapping:
    value = mapping[key]
    process(value)
else:
    handle_missing()
```

**Why agents do this**: Most Python uses EAFP. This codebase uses LBYL.
**Detection**: `grep -r "try:" src/workstack/cli/commands/` should find ~0
**Severity**: 🔴 Critical - Violates core pattern
**Fix**: Convert to if/else check → See patterns.md:353-365

---

### Mistake #2: path.resolve() Without .exists() 🔥 CRITICAL

```python
# ❌ WRONG - Can raise OSError
wt_path_resolved = wt_path.resolve()
if current_dir.is_relative_to(wt_path_resolved):
    ...

# ✅ RIGHT - Check exists first
if wt_path.exists():
    wt_path_resolved = wt_path.resolve()
    if current_dir.is_relative_to(wt_path_resolved):
        ...
```

**Why agents do this**: .resolve() seems safe
**Detection**: `grep -r "\.resolve()" src/ | grep -v "exists()"`
**Severity**: 🔴 Critical - Causes runtime errors
**Fix**: Add exists() check before resolve() → See patterns.md:393-416

---

### Mistake #3: subprocess in Commands 🔴 CRITICAL

```python
# ❌ WRONG - Breaks architecture
@click.command()
def sync_cmd():
    subprocess.run(["git", "fetch"])

# ✅ RIGHT - Use ops interface
@click.command()
@click.pass_obj
def sync_cmd(ctx: WorkstackContext):
    ctx.git_ops.fetch(repo.root)
```

**Why agents do this**: Direct subprocess calls seem simpler
**Detection**: `grep -r "subprocess" src/workstack/cli/commands/`
**Severity**: 🔴 Critical - Blocks testing, breaks DI
**Fix**: Add method to ops interface → See ARCHITECTURE.md:64-93

---

### Mistake #4: Mutating Fake State 🟡 IMPORTANT

```python
# ❌ WRONG - Methods don't exist
git_ops = FakeGitOps()
git_ops.add_worktree(...)  # No such method!
git_ops.worktrees = [...]  # Can't mutate frozen!

# ✅ RIGHT - All state via constructor
git_ops = FakeGitOps(
    worktrees=[
        WorktreeInfo(path=Path("/repo"), branch="main"),
    ],
    git_common_dirs={Path("/repo"): Path("/repo/.git")},
)
```

**Why agents do this**: Expects mutable test doubles
**Detection**: Test failures with AttributeError
**Severity**: 🟡 Important - Test fails
**Fix**: Pass all state via constructor → See tests/CLAUDE.md:23-51

---

### Mistake #5: Forgetting @click.pass_obj 🟡 IMPORTANT

```python
# ❌ WRONG - No context
@click.command("create")
def create(name: str):
    # How do I access git_ops?
    pass

# ✅ RIGHT - Inject context
@click.command("create")
@click.pass_obj
def create(ctx: WorkstackContext, name: str):
    ctx.git_ops.list_worktrees(repo.root)
```

**Why agents do this**: Forgot decorator
**Detection**: Test fails with "missing 1 required positional argument"
**Severity**: 🟡 Important - Runtime error
**Fix**: Add @click.pass_obj decorator → See patterns.md:593-616

---

### Mistake #6: Using print() Not click.echo() 🟢 STYLE

```python
# ❌ WRONG
print("Created worktree")

# ✅ RIGHT
click.echo("Created worktree")
```

**Why agents do this**: Habit
**Detection**: `grep -r "print(" src/workstack/cli/commands/`
**Severity**: 🟢 Style - Works but wrong
**Fix**: Replace with click.echo() → See patterns.md:624-627

---

### Mistake #7: Deep Nesting (>4 Levels) 🟢 STYLE

```python
# ❌ WRONG - 5 levels
def process(data):
    if data:                      # 1
        if validate(data):        # 2
            for item in data:     # 3
                if item.valid:    # 4
                    if save(item): # 5 - TOO DEEP
                        return True

# ✅ RIGHT - Early returns
def process(data):
    if not data: return False
    if not validate(data): return False
    for item in data:
        if not item.valid: continue
        if not save(item): return False
    return True
```

**Why agents do this**: Nested logic feels natural
**Detection**: Look for deeply indented code
**Severity**: 🟢 Style - Harder to read
**Fix**: Extract functions or use early returns → See patterns.md:447-516

---

### Mistake #8: Relative Imports 🟡 IMPORTANT

```python
# ❌ WRONG
from .config import load_config
from ..core import discover_repo_context

# ✅ RIGHT
from workstack.config import load_config
from workstack.core import discover_repo_context
```

**Why agents do this**: Seems shorter
**Detection**: `grep -r "from \." src/workstack/`
**Severity**: 🟡 Important - Against standards
**Fix**: Use full module path → See patterns.md:317-327

---

### Mistake #9: Using Protocol Not ABC 🟡 IMPORTANT

```python
# ❌ WRONG
from typing import Protocol

class GitOps(Protocol):
    def list_worktrees(self) -> list: ...

# ✅ RIGHT
from abc import ABC, abstractmethod

class GitOps(ABC):
    @abstractmethod
    def list_worktrees(self) -> list: ...
```

**Why agents do this**: Protocol seems modern
**Detection**: `grep -r "Protocol" src/workstack/`
**Severity**: 🟡 Important - Wrong pattern
**Fix**: Use ABC with @abstractmethod → See patterns.md:115-158

---

### Mistake #10: Forgetting frozen=True 🟡 IMPORTANT

```python
# ❌ WRONG
@dataclass
class Config:
    value: str

# ✅ RIGHT
@dataclass(frozen=True)
class Config:
    value: str
```

**Why agents do this**: Forgets frozen=True
**Detection**: `grep -r "@dataclass" src/ | grep -v "frozen"`
**Severity**: 🟡 Important - Not immutable
**Fix**: Add frozen=True → See patterns.md:87-109

---

## 📁 Where Things Live

```
src/workstack/
├── cli/
│   ├── cli.py              # Click entry point
│   ├── core.py             # Repo discovery + helpers
│   ├── config.py           # Repo config loader
│   ├── commands/*.py       # CLI commands (Click)
│   └── shell_integration/  # Wrapper scripts + handler
├── core/
│   ├── context.py          # WorkstackContext factory
│   └── *_ops.py            # External operations (ABC + Real)
└── status/                 # Status collectors + renderers

tests/
├── fakes/*.py              # In-memory implementations
├── commands/test_*.py      # Command tests (use fakes)
└── integration/            # Real git tests
```

---

## 🎯 Common Tasks

### Add New Command

1. Create `src/workstack/cli/commands/my_cmd.py`
2. Pattern: `cli/commands/rename.py` (simple) or `cli/commands/create.py` (complex)
3. Add `@click.command()` and `@click.pass_obj`
4. Register in `cli/cli.py`: `cli.add_command(my_cmd)`
5. Write tests in `tests/commands/test_my_cmd.py`

### Add New Operation

1. Create ABC in `src/workstack/core/my_ops.py`
2. Implement `RealMyOps` and `DryRunMyOps`
3. Create `tests/fakes/my_ops.py` with `FakeMyOps`
4. Add to `WorkstackContext` in `core/context.py`
5. Update `create_context()` in `core/context.py`

### Write Test

1. Use `CliRunner()` with `isolated_filesystem()`
2. Create fakes with state via constructor
3. Build `WorkstackContext` with fakes
4. Invoke: `runner.invoke(cli, ["cmd"], obj=test_ctx)`
5. Assert on `result.exit_code` and `result.output`

---

## 🔍 Quick Debugging

```python
# Add debug output (always to stderr)
click.echo(f"DEBUG: {variable=}", err=True)
click.echo(f"DEBUG: {ctx.git_ops=}", err=True)
click.echo(f"DEBUG: {Path.cwd()=}", err=True)

# Check fake state
click.echo(f"DEBUG: Fake worktrees: {git_ops._worktrees}", err=True)
```

### Common Errors → Solutions

| Error                                                          | Cause                 | Solution                          |
| -------------------------------------------------------------- | --------------------- | --------------------------------- |
| `CalledProcessError: git worktree add`                         | Branch exists         | Use different branch or `--force` |
| `FileNotFoundError: .git`                                      | Not in git repo       | `cd` to repo or `git init`        |
| `AttributeError: 'FakeGitOps' has no attribute 'add_worktree'` | Trying to mutate fake | Pass state via constructor        |
| `AssertionError: exit_code == 0`                               | Command failed        | Check `result.output` for error   |
| `missing 1 required positional argument: 'ctx'`                | Forgot decorator      | Add `@click.pass_obj`             |

---

## 🧪 Testing Pattern

```python
def test_my_feature():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # 1. Setup filesystem
        cwd = Path.cwd()

        # 2. Configure fakes
        git_ops = FakeGitOps(
            worktrees=[...],
            git_common_dirs={cwd: cwd / ".git"}
        )

        # 3. Create context
        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=FakeGlobalConfigOps(...),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            dry_run=False,
        )

        # 4. Invoke
        result = runner.invoke(cli, ["cmd"], obj=ctx)

        # 5. Assert
        assert result.exit_code == 0
        assert "expected" in result.output
```

---

## ⚙️ Dev Commands

```bash
# Run tests
uv run pytest                    # All tests
uv run pytest -k test_name       # Specific test

# Type checking (must pass)
uv run pyright

# Formatting
uv run ruff format
uv run ruff check

# Run CLI locally
uv run workstack --help
```

---

## 📖 Documentation Index

| Need to...             | Read...                    |
| ---------------------- | -------------------------- |
| Understand terminology | ../GLOSSARY.md             |
| See architecture       | ../.agent/ARCHITECTURE.md  |
| Learn coding rules     | ../CLAUDE.md               |
| See code patterns      | patterns.md                |
| Understand exceptions  | exception-handling.md      |
| Learn testing          | ../../tests/CLAUDE.md      |
| Find a feature         | ../.agent/FEATURE_INDEX.md |
| Quick reference        | QUICK_REFERENCE.md         |

---

## 🎓 Learning Path

1. **Start here** → This cheat sheet
2. **Understand terms** → ../GLOSSARY.md
3. **See big picture** → ../.agent/ARCHITECTURE.md
4. **Learn patterns** → patterns.md
5. **Deep dive rules** → ../CLAUDE.md

---

## 🔥 Top 3 Critical Rules

1. **LBYL not EAFP** - Check conditions with if/else, not try/except
2. **Check .exists() before .resolve()** - Avoid OSError
3. **Use ops via context** - Never subprocess in commands

**Remember**: When in doubt, find similar code and follow its pattern.

---

## 💡 Quick Decision Tree

```
Should I use try/except?
├─ Is this CLI error boundary? NO → Use if/else
├─ Is this API availability check (gh, gt)? NO → Use if/else
└─ Is this resource cleanup? NO → Use if/else
   └─ YES to any? → OK, document why in comment
```

---

**💡 Pro tip**: If you're about to write try/except, stop and ask: "Can I check this condition first?"

99% of the time, the answer is YES.
