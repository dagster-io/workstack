# Workstack Rules Card

**Purpose**: Ultra-compact reference (500 tokens) for experienced agents

**When to use**: Quick reminder when you know the codebase

**For details**: See cheatsheet.md (2K tokens) or patterns.md (8.5K tokens)

---

## ✅ DO (Always)

```python
# Exception Handling - LBYL
if key in dict: value = dict[key]           # Check first
if path.exists(): path.resolve()            # Check before resolve

# Types - Python 3.13+
list[str], dict[str, int], str | None       # Lowercase built-ins

# Dependency Injection
class Ops(ABC): @abstractmethod ...         # ABC not Protocol
@dataclass(frozen=True) class X: ...        # Always frozen

# Imports
from workstack.module import x              # Absolute only

# CLI
@click.pass_obj                             # Inject context
click.echo("msg")                           # Not print()
ctx.git_ops.method()                        # Use ops via context

# Testing
FakeOps(state=..., config=...)              # All state via constructor
```

---

## ❌ DON'T (Never)

```python
try: dict[key] except KeyError: ...         # ❌ Use if/else
path.resolve()  # without exists()          # ❌ Check first
subprocess.run() in commands/               # ❌ Use ctx.ops
from .module import                         # ❌ Use absolute
@dataclass without frozen=True              # ❌ Always frozen
class Ops(Protocol):                        # ❌ Use ABC
print("msg")                                # ❌ Use click.echo()
fake.add_state()                            # ❌ Pass via constructor
```

---

## 🔥 Critical Rules (Top 3)

1. **LBYL not EAFP** - Check with `if`, not `try/except`
2. **path.exists() before resolve()** - Avoid OSError
3. **ops via context** - Never `subprocess` in commands

**Detection:**

```bash
grep -r "try:" src/workstack/cli/commands/      # Should find ~0
grep -r "\.resolve()" src/ | grep -v exists # Should find ~0
grep -r "subprocess" src/workstack/cli/commands # Should find ~1-2 (script mode only)
```

---

## 🎯 Quick Patterns

### Add Command

1. `src/workstack/cli/commands/my_cmd.py`
2. `@click.command()` + `@click.pass_obj`
3. `repo = discover_repo_context(ctx, Path.cwd())`
4. Use `ctx.git_ops`, `ctx.github_ops`, etc.
5. Register in `cli/cli.py`: `cli.add_command(my_cmd)`

### Add Ops

1. ABC in `src/workstack/core/my_ops.py`
2. `RealMyOps(MyOps)` + `DryRunMyOps(MyOps)`
3. `FakeMyOps(MyOps)` in `tests/fakes/`
4. Add to `WorkstackContext`
5. Update `create_context()` in `core/context.py`

### Test

1. `CliRunner()` + `isolated_filesystem()`
2. Create fakes: `FakeGitOps(worktrees=[...], git_common_dirs={...})`
3. Build context: `WorkstackContext(git_ops=..., ...)`
4. Invoke: `runner.invoke(cli, ["cmd"], obj=ctx)`
5. Assert: `result.exit_code == 0` + `result.output`

---

## 📁 Quick Nav

```
src/workstack/
├── cli/
│   ├── cli.py              # Click entry point
│   ├── core.py             # Repo discovery / path helpers
│   ├── config.py           # Repo config loader
│   ├── commands/*.py       # CLI commands (@click.pass_obj)
│   └── shell_integration/  # Wrapper scripts + handler
├── core/
│   ├── context.py          # WorkstackContext factory
│   └── *_ops.py            # External operations (ABC + Real)
└── status/                 # Status collectors + renderers

tests/
├── fakes/*.py              # In-memory fakes (state via constructor)
└── commands/               # Command tests (use fakes)
```

---

## 🚨 Common Errors

| Error                                              | Fix                               |
| -------------------------------------------------- | --------------------------------- |
| `AttributeError: FakeGitOps has no 'add_worktree'` | Pass state via constructor        |
| `missing 1 required positional argument: 'ctx'`    | Add `@click.pass_obj`             |
| `FileNotFoundError: .git`                          | `cd` to git repo                  |
| `CalledProcessError: git worktree add`             | Branch exists, use different name |

---

## 📖 Detailed Docs

| Need                 | Read                      | Tokens |
| -------------------- | ------------------------- | ------ |
| Quick ref + mistakes | cheatsheet.md             | 2,000  |
| Detailed patterns    | patterns.md               | 8,500  |
| Architecture         | ../.agent/ARCHITECTURE.md | 4,000  |
| Terminology          | ../GLOSSARY.md            | 2,000  |
| Exception handling   | exception-handling.md     | 5,000  |
| Testing              | ../../tests/CLAUDE.md     | 3,000  |

---

## 💡 Decision Trees

**try/except?**

- CLI boundary? YES → OK | NO → Use if/else
- API check (gh/gt)? YES → OK | NO → Use if/else
- Resource cleanup? YES → OK | NO → Use if/else

**Max indent: 4 levels** - Extract function if deeper

**Default args?** - Avoid unless commented why

---

## ⚙️ Dev Commands

```bash
uv run pytest              # All tests
uv run pyright             # Type check (must pass)
uv run ruff format         # Format
uv run workstack --help    # Run locally
```

---

**💡 Remember**: When in doubt, find similar code and copy its pattern.
