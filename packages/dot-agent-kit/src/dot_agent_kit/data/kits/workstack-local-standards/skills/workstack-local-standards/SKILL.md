---
name: workstack-local-standards
description: This skill should be used when working on workstack-specific code. Use when writing, reviewing, or refactoring code to ensure adherence to workstack naming conventions, architecture patterns, and documentation standards. Essential for maintaining consistency with project-specific conventions beyond Python 3.13+ standards.
---

# Workstack Local Coding Standards

Project-specific conventions for workstack development that complement dignified-python standards.

---

## CRITICAL RULES

### 1. Naming Conventions 🔴

**Claude Artifacts (`.claude/` directory):**

```bash
# ✅ CORRECT: kebab-case for .claude/ artifacts
.claude/commands/submit-branch.md
.claude/skills/local-coding-standards/
.claude/agents/branch-submitter.md
.claude/hooks/compliance-reminder.md

# ❌ WRONG: snake_case for Claude artifacts
.claude/commands/submit_branch.md
.claude/skills/local_coding_standards/
```

**Python Code:**

Python naming conventions (snake_case, PascalCase, UPPER_SNAKE_CASE) are covered in the dignified-python-313 skill.

**Brand Names:**

- `GitHub` (not Github)
- `Graphite` (product name, always capitalized)

### 2. Architecture Patterns 🔴

**Ops Abstraction Pattern:**

All external system interactions MUST go through Ops abstractions:

```python
# ✅ CORRECT: Using Ops abstraction
from workstack.core.ops import GitOps

class RealGitOps(GitOps):
    def create_branch(self, branch_name: str, base: str | None = None) -> None:
        ...

# Usage in business logic
def create_feature_branch(ctx: WorkstackContext, name: str) -> None:
    ctx.git_ops.create_branch(name, base="main")

# ❌ WRONG: Direct subprocess calls in business logic
import subprocess

def create_feature_branch(ctx: WorkstackContext, name: str) -> None:
    subprocess.run(["git", "branch", name, "main"], check=True)
```

**Why**: Ops abstractions enable:

- Testing without real git/filesystem/network operations
- Dependency injection for different contexts
- Clear separation between business logic and I/O

**Context Regeneration:**

After operations that invalidate `ctx.cwd`, regenerate context:

```python
# ✅ CORRECT: Regenerate after chdir
from workstack.core.context import regenerate_context

os.chdir(new_directory)
ctx = regenerate_context(ctx, repo_root=repo.root)

# ✅ CORRECT: Regenerate after worktree removal
if removed_current_worktree:
    os.chdir(safe_directory)
    ctx = regenerate_context(ctx, repo_root=repo.root)

# ❌ WRONG: Using stale context after chdir
os.chdir(new_directory)
# ctx.cwd is now stale - will cause FileNotFoundError
```

**Why**: `ctx.cwd` is captured once at CLI entry. After `os.chdir()`, it becomes stale.

### 3. Documentation Patterns 🟡

**Docstring Format:**

```python
# ✅ CORRECT: Clear, concise docstrings
def create_worktree(name: str, branch: str) -> Path:
    """Create a new worktree with the given name and branch.

    Args:
        name: Worktree name (must be unique)
        branch: Branch to checkout in worktree

    Returns:
        Path to created worktree

    Raises:
        WorktreeExistsError: If worktree with name already exists
        GitError: If git command fails
    """
    ...

# ❌ WRONG: Missing details or overly verbose
def create_worktree(name: str, branch: str) -> Path:
    """Create worktree."""  # Too minimal
    ...

def create_worktree(name: str, branch: str) -> Path:
    """
    This function creates a new worktree by first checking if the name
    is unique, then validating the branch exists, then running the git
    worktree add command with appropriate flags...
    """  # Too verbose - describes implementation, not interface
    ...
```

**Inline Comments:**

```python
# ✅ CORRECT: Explain WHY, not WHAT
# Must regenerate context because os.chdir() invalidates ctx.cwd
ctx = regenerate_context(ctx, repo_root=repo.root)

# Graphite stores branch metadata in git config (gt.branch-parent)
parent_branch = git_ops.get_config_value(f"gt.branch-parent.{branch}")

# ✅ CORRECT: Document non-obvious edge cases
# Empty string is valid worktree name in git but causes UI issues
if not name or not name.strip():
    raise ValueError("Worktree name cannot be empty")

# ❌ WRONG: Describing obvious code
# Create a variable to hold the branch name
branch_name = "main"

# Call the create_worktree function
create_worktree(branch_name)
```

---

## PATTERN REFERENCE

### Agent Execution (Cost & Context Optimization)

**ALWAYS use Task tool with appropriate agent for CLI tools:**

```python
# ✅ CORRECT: Use runner agent for CLI tools
Task(
    subagent_type="runner",
    description="Run CI checks",
    prompt="Execute: make all-ci"
)

Task(
    subagent_type="runner",
    description="Run tests",
    prompt="Execute: uv run pytest tests/"
)

# ✅ CORRECT: Use specialized agent for workflows
Task(
    subagent_type="gt-branch-submitter",
    description="Submit branch to Graphite",
    prompt="Execute submit-branch workflow"
)

# ❌ WRONG: Direct Bash for CLI tools (wastes tokens, pollutes context)
Bash("make all-ci")
Bash("uv run pytest tests/")
Bash("gt submit --publish")
```

**What can use Bash directly:**

- Git read-only operations: `git status`, `git log`, `git diff`
- File system operations: `ls`, `cat`, `find`
- Simple shell commands: `echo`, `pwd`

### Graphite Stack Terminology

**Visualize trunk at BOTTOM:**

```
TOP ↑    feat-3  ← upstack (leaf)
         feat-2
         feat-1
BOTTOM ↓ main    ← downstack (trunk)
```

**Directional terms:**

- **UPSTACK / UP** = away from trunk = toward TOP = toward leaves
- **DOWNSTACK / DOWN** = toward trunk = toward BOTTOM = toward main

**Example:**

Given stack: `main → feat-1 → feat-2 → feat-3`

If current branch is `feat-1`:

- Upstack: `feat-2`, `feat-3` (children, toward top)
- Downstack: `main` (parent, toward bottom)

**Common mistake:** Thinking "upstack" means "toward main" ❌

**Correct:** upstack = away from main ✅

### CLI Output Styling

**Use `click.style()` consistently:**

| Element          | Color            | Bold | Example                                             |
| ---------------- | ---------------- | ---- | --------------------------------------------------- |
| Branch names     | `yellow`         | No   | `click.style(branch, fg="yellow")`                  |
| PR numbers       | `cyan`           | No   | `click.style(f"PR #{pr}", fg="cyan")`               |
| PR titles        | `bright_magenta` | No   | `click.style(title, fg="bright_magenta")`           |
| Success (✓)      | `green`          | No   | `click.style("✓ Done", fg="green")`                 |
| Section headers  | -                | Yes  | `click.style(header, bold=True)`                    |
| Current branch   | `bright_green`   | Yes  | `click.style(branch, fg="bright_green", bold=True)` |
| Paths (complete) | `green`          | No   | `click.style(str(path), fg="green")`                |
| Paths (metadata) | `white`          | Dim  | `click.style(str(path), fg="white", dim=True)`      |
| Errors           | `red`            | No   | `click.style("Error", fg="red")`                    |
| Dry run markers  | `bright_black`   | No   | `click.style("(dry run)", fg="bright_black")`       |
| Worktree names   | `cyan`           | Yes  | `click.style(name, fg="cyan", bold=True)`           |

**Emoji conventions:**

- `✓` - Success indicators
- `✅` - Major success/completion
- `❌` - Errors/failures
- `📋` - Lists/plans
- `🗑️` - Deletion operations
- `⭕` - Aborted/cancelled
- `ℹ️` - Info notes

**Spacing:**

```python
# ✅ CORRECT: Vertical spacing for sections
click.echo("Section 1 content")
click.echo()  # Empty line
click.echo("Section 2 content")

# ✅ CORRECT: Indent list items
click.echo("  • Item 1")
click.echo("  • Item 2")
```

### Testing Patterns

**NEVER use hardcoded paths in tests:**

```python
# ❌ CATASTROPHICALLY DANGEROUS
def test_something():
    cwd = Path("/test/default/cwd")  # Hardcoded path
    ctx = WorkstackContext(..., cwd=cwd)

# ✅ CORRECT: Use proper fixtures
def test_something(tmp_path: Path) -> None:
    ctx = WorkstackContext(..., cwd=tmp_path)

# ✅ CORRECT: Use simulated environment
def test_something():
    with simulated_workstack_env(runner) as env:
        ctx = WorkstackContext(..., cwd=env.cwd)
```

**Why hardcoded paths are catastrophic:**

- Code may write `.workstack` files at hardcoded paths, polluting real filesystem
- Tests appear isolated but share state through hardcoded paths
- Security risk: Creating files at system paths can be exploited

**CLI Testing:**

```python
# ✅ CORRECT: Use CliRunner (fast, in-memory)
from click.testing import CliRunner

def test_command():
    runner = CliRunner()
    result = runner.invoke(my_command, ["--arg", "value"])
    assert result.exit_code == 0

# ❌ WRONG: Use subprocess (slow, real I/O)
def test_command():
    result = subprocess.run(["workstack", "command"], ...)
```

---

## ANTI-PATTERNS TO AVOID

### 1. Mixing Naming Conventions

```bash
# ❌ WRONG: Using snake_case for Claude artifacts
.claude/commands/my_command.md
.claude/skills/my_skill/

# ✅ CORRECT: kebab-case for Claude artifacts
.claude/commands/my-command.md
.claude/skills/my-skill/
```

### 2. Direct System Calls in Business Logic

```python
# ❌ WRONG: Calling subprocess directly
def create_branch(name: str) -> None:
    subprocess.run(["git", "branch", name], check=True)

# ✅ CORRECT: Using Ops abstraction
def create_branch(ctx: WorkstackContext, name: str) -> None:
    ctx.git_ops.create_branch(name)
```

### 3. Using Stale Context After Directory Changes

```python
# ❌ WRONG: Context becomes stale after chdir
os.chdir(new_dir)
# ctx.cwd still points to old directory
result = ctx.some_operation()  # May fail with FileNotFoundError

# ✅ CORRECT: Regenerate context after chdir
os.chdir(new_dir)
ctx = regenerate_context(ctx, repo_root=repo.root)
result = ctx.some_operation()
```

### 4. Speculative Tests

```python
# ❌ FORBIDDEN: Tests for future features
# def test_feature_we_might_add_later():
#     """Placeholder for potential feature."""
#     pass

# ✅ CORRECT: TDD for current feature
def test_new_feature_being_built_now():
    """Test for feature I'm implementing right now."""
    result = feature_function()
    assert result == expected_value
```

---

## CHECKLIST BEFORE WRITING CODE

Before creating `.claude/` artifacts:

- [ ] Am I using `kebab-case` for filenames?
- [ ] Have I checked no conflicts with existing artifact names?

Before writing Python code:

- [ ] Am I using Ops abstractions for external system calls?
- [ ] Have I checked if context regeneration is needed after `os.chdir()`?
- [ ] Am I using `click.echo()` for CLI output (not `print()`)?
- [ ] Have I applied consistent color styling with `click.style()`?

Before writing tests:

- [ ] Am I using `tmp_path` fixture or `simulated_workstack_env`?
- [ ] Have I avoided ALL hardcoded paths (no `Path("/test/...")`)?
- [ ] Am I using `CliRunner` for CLI tests (not subprocess)?
- [ ] Am I only testing actively implemented code (no speculative tests)?

Before using CLI tools:

- [ ] Am I using Task tool with runner agent (not direct Bash)?
- [ ] Is this a read-only git operation (then Bash is OK)?

Before documenting code:

- [ ] Have I explained WHY, not just WHAT?
- [ ] Are my docstrings clear and complete (Args, Returns, Raises)?
- [ ] Have I documented non-obvious edge cases?

---

## QUICK DECISION TREE

**Creating a file in `.claude/`?**

- → Use `kebab-case` (hyphens, not underscores)

**Making external system calls (git, filesystem, network)?**

- → Use Ops abstractions (`ctx.git_ops`, `ctx.file_ops`, etc.)
- → Exception: Read-only git commands can use Bash directly

**Changed directory with `os.chdir()`?**

- → Regenerate context with `regenerate_context(ctx, repo_root)`

**Running CLI tools (`make`, `pytest`, `ruff`, `gt`)?**

- → Use Task tool with runner agent (not Bash)
- → Exception: Simple read-only commands

**Writing tests?**

- → Use `tmp_path` fixture or `simulated_workstack_env`
- → NEVER use hardcoded paths like `Path("/test/...")`
- → Use `CliRunner` for CLI tests (not subprocess)

**Referring to Graphite stack direction?**

- → Upstack = away from main (toward leaves)
- → Downstack = toward main (toward trunk)

**Adding CLI output?**

- → Use `click.style()` with consistent colors
- → Use standard emoji conventions
- → Add spacing between sections

---

## REFERENCES

- Dignified Python standards: Load `dignified-python-313` skill
- Testing patterns: `docs/agent/testing.md`
- Project glossary: `docs/agent/glossary.md`
- Documentation guide: `docs/agent/guide.md`
