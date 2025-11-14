### devrun (v0.1.0)

**Purpose**: Cost-optimized agent for executing development CLI tools (pytest, pyright, ruff, prettier, make, gt) with automatic output parsing and context isolation

**Artifacts**:

- agent: agents/devrun/devrun.md
- doc: docs/devrun/tools/gt.md, docs/devrun/tools/make.md, docs/devrun/tools/prettier.md, docs/devrun/tools/pyright.md, docs/devrun/tools/pytest.md, docs/devrun/tools/ruff.md

**🔴 CRITICAL USAGE RULES**:

**ALWAYS route these tools through devrun agent (NEVER use Bash directly):**

- `make` (any variant) - `make all-ci`, `make test`, `make format`, etc.
- `pytest` (any variant) - `pytest`, `uv run pytest`, `python -m pytest`
- `pyright` (any variant) - `pyright`, `uv run pyright`
- `ruff` (any variant) - `ruff check`, `ruff format`, `uv run ruff`
- `prettier` - Use via `make prettier`
- `gt` (all Graphite commands) - `gt submit`, `gt status`, etc.

**Why mandatory routing:**

- Token efficiency: Subagent context doesn't pollute parent agent
- Cost optimization: Uses Haiku model (cheaper than Sonnet)
- Output parsing: Automatically parses tool output
- Context isolation: Large outputs stay in subagent

**Invocation pattern:**

```python
Task(
    subagent_type="devrun",
    description="Brief description",
    prompt="Execute: <command>"
)
```

**Command syntax flexibility:**

The agent accepts commands in any form and executes verbatim. Route through agent regardless of syntax:

- `pytest tests/` OR `uv run pytest tests/` - both work
- `pyright src/` OR `uv run pyright src/` - both work
- `ruff check .` OR `uv run ruff check .` - both work

**Common mistakes:**

```python
# ❌ WRONG: Direct Bash (expensive, inefficient)
Bash("make all-ci")
Bash("pytest tests/")
Bash("uv run pytest tests/")
Bash("pyright src/")
Bash("gt submit")

# ✅ CORRECT: Route through devrun agent
Task(subagent_type="devrun", prompt="Execute: make all-ci")
Task(subagent_type="devrun", prompt="Execute: pytest tests/")
Task(subagent_type="devrun", prompt="Execute: pyright src/")
Task(subagent_type="devrun", prompt="Execute: gt submit")
```

**What CAN use Bash directly:**

- Git operations (read-only): `git status`, `git log`, `git diff`
- File operations: `ls`, `cat`, `find`
- Simple shell: `echo`, `pwd`

🔴 Using Bash directly for CLI tools wastes tokens, pollutes context, and bypasses cost optimization.
