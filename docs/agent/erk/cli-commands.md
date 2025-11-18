# Adding CLI Commands with JSON Output

This guide explains how to add CLI commands to erk with JSON output support. It covers the infrastructure, patterns, and testing requirements based on real implementations in the codebase.

## Table of Contents

- [Overview & Quick Start](#overview--quick-start)
- [Output Abstraction (Foundation)](#output-abstraction-foundation)
- [JSON Infrastructure Overview](#json-infrastructure-overview)
- [Pattern 1: Simple Commands](#pattern-1-simple-commands)
- [Pattern 2: Complex Commands](#pattern-2-complex-commands)
- [Pattern 3: Renderer-Based](#pattern-3-renderer-based)
- [Testing Patterns](#testing-patterns)
- [Common Patterns & Conventions](#common-patterns--conventions)
- [Common Pitfalls](#common-pitfalls)
- [Reference Files](#reference-files)

## Overview & Quick Start

### TL;DR: Choose Your Pattern

Use this decision tree to select the right pattern:

```
Is your command output...
├─ Simple single object (name, path, status)?
│  └─ ✅ Use Pattern 1: Simple Commands (--json flag)
│
├─ Complex nested structures (config with sections)?
│  └─ ✅ Use Pattern 2: Complex Commands (--json flag)
│
└─ Already using structured data/renderers?
   └─ ✅ Use Pattern 3: Renderer-Based (--format choice)
```

### Quick Reference Checklist

When adding JSON support to a command:

1. **Choose pattern** based on output complexity (see decision tree above)
2. **Add Pydantic schema** to `src/erk/cli/json_schemas.py` with `ConfigDict(strict=True)`
3. **Add flag/parameter**:
   - Simple/Complex: `@click.option("--json", "output_json", is_flag=True)`
   - Renderer-based: `@click.option("--format", type=click.Choice(["text", "json"]), default="text")`
4. **Add decorator** (renderer-based only): `@json_error_boundary` before `@click.pass_obj`
5. **Collect data** in command logic (business logic unchanged)
6. **Output conditionally**:
   - Simple/Complex: `if output_json:` branch with `emit_json(model.model_dump(mode="json"))`
   - Renderer-based: `renderer = get_renderer(format); renderer.render_X(data)`
7. **Write tests**: Minimum 3 tests (happy path, edge case, schema validation)

## Output Abstraction (Foundation)

All CLI output in erk uses stream separation to enable shell script integration.

### The Two Output Functions

```python
from erk.cli.output import user_output, machine_output

# For human-readable messages (stderr)
user_output("✓ Created worktree feature")
user_output(click.style("Error: ", fg="red") + "Branch not found")

# For structured data (stdout)
machine_output(json_str)
machine_output(str(activation_path))
```

### Why Stream Separation Matters

**stderr vs stdout routing:**

- **`user_output()`** → stderr (human-facing status messages)
- **`machine_output()`** → stdout (structured data for scripts)

**Example: Shell integration without interference**

```bash
# JSON data goes to stdout, progress messages go to stderr
$ worktree=$(erk current --json | jq -r .name)
# User still sees: "✓ Found worktree: feature" (on stderr)
# Script captures: {"name": "feature", ...} (from stdout)
```

**When to use each:**

| Use case                 | Function           | Rationale                  |
| ------------------------ | ------------------ | -------------------------- |
| Status messages          | `user_output()`    | User info, won't interfere |
| Error messages           | `user_output()`    | User info, won't interfere |
| Progress indicators      | `user_output()`    | User info, won't interfere |
| Success confirmations    | `user_output()`    | User info, won't interfere |
| JSON output              | `machine_output()` | Script data, needs stdout  |
| Shell activation scripts | `machine_output()` | Script data, needs stdout  |
| Paths for script capture | `machine_output()` | Script data, needs stdout  |

**Reference implementations:**

- `src/erk/cli/commands/current.py:52` - Uses `user_output()` for text, `emit_json()` (which uses `machine_output()`) for JSON
- `src/erk/cli/commands/config.py:99-125` - Uses `user_output()` for config listing
- `src/erk/cli/json_output.py:61-80` - `emit_json()` uses `machine_output()` internally

## JSON Infrastructure Overview

### Core Utilities

All JSON infrastructure lives in `src/erk/cli/json_output.py`.

#### `emit_json()` - Main Output Function

```python
def emit_json(data: dict[str, Any]) -> None:
    """Output JSON data to stdout for machine consumption.

    IMPORTANT: Only accepts dicts, not Pydantic models directly.
    Call model.model_dump(mode='json') before passing to this function.
    """
```

**Key characteristics:**

- **Dict-only interface** - Forces explicit conversion from Pydantic models
- **Automatic serialization** - Handles Path, datetime, dataclass via `_serialize_for_json()`
- **Routes to stdout** - Uses `machine_output()` for stream separation

**Example usage:**

```python
from erk.cli.json_output import emit_json

# ✅ CORRECT: Convert Pydantic model to dict first
response = CurrentCommandResponse(name="feature", path=str(path), is_root=False)
emit_json(response.model_dump(mode="json"))

# ❌ WRONG: Passing Pydantic model directly
emit_json(response)  # Type error!
```

#### `_serialize_for_json()` - Special Type Handling

```python
def _serialize_for_json(obj: Any) -> Any:
    """Recursively serialize special types for JSON.

    Handles:
    - Path → str
    - datetime → ISO format string
    - dataclass → dict (recursively)
    """
```

**What it handles:**

- **Path objects** → `str(path)`
- **datetime objects** → `obj.isoformat()`
- **dataclass instances** → `asdict(obj)` then recurse
- **Nested structures** → Recursively processes dicts and lists

**Note:** This is for plain dict structures. Pydantic models use `model.model_dump(mode="json")` which handles these types automatically via field type annotations.

#### `@json_error_boundary` - Error Handling Decorator

```python
@json_error_boundary
def my_command(format: str) -> None:
    """Decorator catches exceptions in JSON mode."""
```

**How it works:**

- Inspects `format` parameter in kwargs
- If `format == "json"`, catches exceptions and outputs structured JSON errors
- Otherwise, lets exceptions bubble up normally
- Always lets `SystemExit` pass through

**When to use:**

- ✅ Use with `--format` parameter (Pattern 3: Renderer-Based)
- ❌ Don't use with `--json` boolean flag (Patterns 1 & 2)

**Decorator order (renderer-based commands):**

```python
@click.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@json_error_boundary  # ← Before @click.pass_obj
@click.pass_obj
def my_command(ctx: ErkContext, format: str) -> None:
    ...
```

### Pydantic Schema Conventions

All response schemas live in `src/erk/cli/json_schemas.py`.

#### Basic Schema Structure

```python
from pydantic import BaseModel, ConfigDict, Field

class MyCommandResponse(BaseModel):
    """JSON response schema for the `erk mycommand` command.

    Attributes:
        field1: Description
        field2: Description
    """

    model_config = ConfigDict(strict=True)  # ← Always use strict validation

    field1: str
    field2: int
```

**Key conventions:**

- **Always use `ConfigDict(strict=True)`** - Enables runtime validation
- **Use docstrings** - Document the schema purpose and fields
- **Path fields as `str`** - Never use `Path` type in schemas (convert at construction)
- **Optional fields as `X | None`** - Use modern Python 3.13+ union syntax
- **Field constraints** - Use `Field(...)` for validation (e.g., `pattern="^(open|closed)$"`)

#### Path Handling in Schemas

```python
# ❌ WRONG: Path type in schema
class WorktreeInfo(BaseModel):
    path: Path  # Will cause issues

# ✅ CORRECT: str in schema, convert at construction
class WorktreeInfo(BaseModel):
    path: str

# Usage: Convert Path to str when constructing
info = WorktreeInfo(path=str(worktree_path))
```

**Why `str` not `Path`:**

- Pydantic can serialize Path fields, but keeping schemas as primitive types is clearer
- Explicit conversion at construction time (LBYL principle)
- Matches JSON's native string type

#### Optional Fields

```python
class StatusInfo(BaseModel):
    branch: str | None  # ← Modern Python 3.13+ syntax
    pr_number: int | None
    plan_file: str | None

    # ❌ WRONG: Old typing syntax
    # branch: Optional[str]  # Don't use this
```

## Pattern 1: Simple Commands

**When to use:** Single object response with straightforward structure.

**Example command:** `erk current` - outputs current worktree information.

### Step-by-Step Implementation

#### 1. Define Pydantic Schema

**File:** `src/erk/cli/json_schemas.py`

```python
class CurrentCommandResponse(BaseModel):
    """JSON response schema for the `erk current` command.

    Attributes:
        name: Name of the worktree (or "root" if in root worktree)
        path: Absolute path to the worktree directory
        is_root: Whether this is the root worktree
    """

    model_config = ConfigDict(strict=True)

    name: str
    path: str
    is_root: bool
```

**Schema characteristics:**

- Simple flat structure (no nesting)
- All required fields (no `| None`)
- Primitive types (str, bool)

#### 2. Add `--json` Flag to Command

```python
@click.command("current")
@click.option(
    "--json",
    "output_json",  # ← Named parameter avoids shadowing json module
    is_flag=True,
    help="Output JSON format",
)
@click.pass_obj
def current_cmd(ctx: ErkContext, output_json: bool) -> None:
    """Show current erk name."""
```

**Flag naming:**

- Use `"output_json"` as the parameter name to avoid shadowing the `json` module
- Use `is_flag=True` for boolean flags

#### 3. Implement Command Logic

```python
def current_cmd(ctx: ErkContext, output_json: bool) -> None:
    """Show current erk name."""
    # Business logic (unchanged whether JSON or text)
    repo = discover_repo_context(ctx, ctx.cwd)
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    wt_info = find_current_worktree(worktrees, ctx.cwd)

    if wt_info is None:
        raise SystemExit(1)

    # Compute output data
    is_root = is_root_worktree(wt_info.path, repo.root)
    name = "root" if is_root else wt_info.path.name

    # Output based on format
    if output_json:
        response = CurrentCommandResponse(
            name=name,
            path=str(wt_info.path),  # ← Convert Path to str
            is_root=is_root,
        )
        emit_json(response.model_dump(mode="json"))  # ← Note: mode="json"
    else:
        user_output(name)
```

**Key patterns:**

- **Business logic unchanged** - Data collection same for both formats
- **Path conversion** - `str(wt_info.path)` when constructing model
- **Explicit model conversion** - `model.model_dump(mode="json")` before `emit_json()`
- **Stream routing** - `emit_json()` for JSON (stdout), `user_output()` for text (stderr)

**Reference:** `src/erk/cli/commands/current.py:22-52`

### Testing Pattern 1

**Minimum 3 tests required:**

1. **Happy path** - Valid input, verify JSON structure
2. **Edge case** - Root worktree, special values
3. **Schema validation** - Ensure Pydantic model validates correctly

**Example tests:**

```python
import json
from click.testing import CliRunner
from erk.cli.commands.current import current_cmd

def test_current_json_output(erk_inmem_env):
    """Test current command JSON output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(current_cmd, ["--json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["name"] == env.worktree_name
        assert data["path"] == str(env.worktree_path)
        assert data["is_root"] is False

def test_current_json_root_worktree(erk_inmem_env):
    """Test current command JSON output for root worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context(is_root=True)
        result = runner.invoke(current_cmd, ["--json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["name"] == "root"
        assert data["is_root"] is True

def test_current_json_schema_validation():
    """Test that CurrentCommandResponse validates correctly."""
    from erk.cli.json_schemas import CurrentCommandResponse

    # Valid data
    response = CurrentCommandResponse(
        name="feature",
        path="/repo/worktrees/feature",
        is_root=False,
    )
    assert response.name == "feature"

    # Invalid data - missing required field
    with pytest.raises(ValidationError):
        CurrentCommandResponse(name="feature", path="/path")  # Missing is_root
```

**Test fixtures:**

- Use `erk_inmem_env()` context manager for test environment
- Build context with `env.build_context()`
- Parse JSON with `json.loads(result.output)`

**Reference test files:**

- `tests/cli/test_current.py` - Full test suite for current command

## Pattern 2: Complex Commands

**When to use:** Complex nested structures, optional sections, multiple data sources.

**Example command:** `erk config list` - outputs global and repository configuration.

### Step-by-Step Implementation

#### 1. Define Nested Pydantic Schemas

**File:** `src/erk/cli/json_schemas.py`

```python
class GlobalConfigInfo(BaseModel):
    """Global configuration information.

    Attributes:
        erk_root: Path to the erk root directory
        use_graphite: Whether Graphite integration is enabled
        show_pr_info: Whether to show PR information
        exists: Whether the global config file exists
    """

    model_config = ConfigDict(strict=True)

    erk_root: str
    use_graphite: bool
    show_pr_info: bool
    exists: bool


class RepositoryConfigInfo(BaseModel):
    """Repository configuration information.

    Attributes:
        trunk_branch: Trunk branch name or None
        env: Environment variables dict (may be empty)
        post_create_shell: Shell for post-create commands or None
        post_create_commands: Commands to run after worktree creation
    """

    model_config = ConfigDict(strict=True)

    trunk_branch: str | None
    env: dict[str, str]
    post_create_shell: str | None
    post_create_commands: list[str]


class ConfigListResponse(BaseModel):
    """JSON response schema for the `erk config list` command.

    Attributes:
        global_config: Global configuration (None if not configured)
        repository_config: Repository configuration (None if not in repo)
    """

    model_config = ConfigDict(strict=True)

    global_config: GlobalConfigInfo | None
    repository_config: RepositoryConfigInfo | None
```

**Schema characteristics:**

- **Nested structure** - Top-level model contains other models
- **Optional sections** - `| None` for sections that may not exist
- **Optional fields within sections** - `trunk_branch: str | None`
- **Collection types** - `dict[str, str]`, `list[str]`

**Reference:** `src/erk/cli/json_schemas.py:53-109`

#### 2. Add `--json` Flag to Command

```python
@config_group.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
@click.pass_obj
def config_list(ctx: ErkContext, output_json: bool) -> None:
    """Print a list of configuration keys and values."""
```

**Same pattern as Pattern 1** - Boolean flag, renamed parameter.

#### 3. Implement Command Logic with Nested Structure

```python
def config_list(ctx: ErkContext, output_json: bool) -> None:
    """Print a list of configuration keys and values."""
    if output_json:
        from erk.core.repo_discovery import NoRepoSentinel, RepoContext

        # Build global config section
        global_config_info = None
        if ctx.global_config:
            global_config_info = GlobalConfigInfo(
                erk_root=str(ctx.global_config.erk_root),  # ← Path to str
                use_graphite=ctx.global_config.use_graphite,
                show_pr_info=ctx.global_config.show_pr_info,
                exists=True,
            )

        # Build repository config section
        repository_config_info = None
        if isinstance(ctx.repo, RepoContext):
            cfg = ctx.local_config
            repository_config_info = RepositoryConfigInfo(
                trunk_branch=ctx.trunk_branch,  # ← Already str | None
                env=cfg.env,  # ← dict[str, str]
                post_create_shell=cfg.post_create_shell,  # ← str | None
                post_create_commands=cfg.post_create_commands,  # ← list[str]
            )

        # Construct top-level response
        response = ConfigListResponse(
            global_config=global_config_info,
            repository_config=repository_config_info,
        )
        emit_json(response.model_dump(mode="json"))
    else:
        # Text output implementation...
        user_output(click.style("Global configuration:", bold=True))
        # ...
```

**Key patterns:**

- **Conditional section building** - Check if data exists before creating nested models
- **None propagation** - Top-level fields can be `None` if sections don't exist
- **Type preservation** - `dict[str, str]` and `list[str]` pass through directly
- **Path conversion** - Convert Path fields to str when constructing models

**Reference:** `src/erk/cli/commands/config.py:64-134`

### Handling Optional Fields

**Pattern: Check before constructing nested model**

```python
# ❌ WRONG: Constructing model with None values that should skip the section
if ctx.global_config is None:
    global_config_info = GlobalConfigInfo(
        erk_root=None,  # Type error: expects str, not None
        use_graphite=False,
        show_pr_info=False,
        exists=False,
    )

# ✅ CORRECT: Set entire section to None if not available
global_config_info = None
if ctx.global_config:
    global_config_info = GlobalConfigInfo(
        erk_root=str(ctx.global_config.erk_root),
        use_graphite=ctx.global_config.use_graphite,
        show_pr_info=ctx.global_config.show_pr_info,
        exists=True,
    )

# Top-level model accepts None for optional sections
response = ConfigListResponse(
    global_config=global_config_info,  # ← Can be None
    repository_config=repository_config_info,  # ← Can be None
)
```

### Testing Pattern 2

**Minimum 5+ tests required for complex structures:**

1. **Happy path** - All sections present
2. **Partial data** - Only global config exists
3. **Partial data** - Only repo config exists
4. **Empty sections** - Empty dicts/lists
5. **Schema validation** - Nested model validation

**Example tests:**

```python
def test_config_list_json_full(erk_inmem_env):
    """Test config list JSON with all sections."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(config_list, ["--json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        # Validate global config section
        assert data["global_config"] is not None
        assert "erk_root" in data["global_config"]
        assert data["global_config"]["exists"] is True

        # Validate repository config section
        assert data["repository_config"] is not None
        assert "trunk_branch" in data["repository_config"]

def test_config_list_json_global_only(erk_inmem_env):
    """Test config list JSON with only global config."""
    runner = CliRunner()
    with erk_inmem_env(runner, no_repo=True) as env:
        ctx = env.build_context()
        result = runner.invoke(config_list, ["--json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["global_config"] is not None
        assert data["repository_config"] is None  # ← No repo

def test_config_list_json_empty_collections(erk_inmem_env):
    """Test config list JSON with empty dicts/lists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(config_list, ["--json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        repo_config = data["repository_config"]
        assert repo_config["env"] == {}  # ← Empty dict
        assert repo_config["post_create_commands"] == []  # ← Empty list

def test_config_list_schema_validation():
    """Test ConfigListResponse validates nested structures."""
    from erk.cli.json_schemas import ConfigListResponse, GlobalConfigInfo

    # Valid nested structure
    response = ConfigListResponse(
        global_config=GlobalConfigInfo(
            erk_root="/home/user/.erk",
            use_graphite=True,
            show_pr_info=False,
            exists=True,
        ),
        repository_config=None,
    )
    assert response.global_config.erk_root == "/home/user/.erk"

    # Invalid - missing required field in nested model
    with pytest.raises(ValidationError):
        ConfigListResponse(
            global_config=GlobalConfigInfo(
                erk_root="/path",
                use_graphite=True,
                # Missing show_pr_info
            ),
            repository_config=None,
        )
```

## Pattern 3: Renderer-Based

**When to use:** Existing structured data, multiple output modes, complex formatting.

**Example command:** `erk status` - outputs comprehensive worktree status.

### Renderer Abstraction

**File:** `src/erk/cli/rendering.py`

The renderer framework separates data collection from presentation.

#### OutputRenderer ABC

```python
from abc import ABC, abstractmethod

class OutputRenderer(ABC):
    """Base class for output renderers."""

    @abstractmethod
    def render_simple(self, data: dict[str, Any]) -> None:
        """Render simple key-value data."""
        pass

    @abstractmethod
    def render_list(self, data: dict[str, Any]) -> None:
        """Render worktree list data."""
        pass

    @abstractmethod
    def render_status(self, status_data: Any) -> None:
        """Render status data."""
        pass
```

**Design principles:**

- **Single data collection path** - Business logic runs once
- **Format decision deferred** - Renderer chosen based on `--format` parameter
- **No duplication** - Text and JSON formatters share same data source

#### TextRenderer Implementation

```python
class TextRenderer(OutputRenderer):
    """Renders output as formatted text for human consumption."""

    def render_simple(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            user_output(f"{key}: {value}")  # ← Goes to stderr

    def render_status(self, status_data: Any) -> None:
        from erk.status.renderers.simple import SimpleRenderer
        SimpleRenderer().render(status_data)  # ← Delegates to existing renderer
```

**Characteristics:**

- Uses `user_output()` (stderr)
- Formats for human readability
- Can delegate to existing rendering logic

#### JsonRenderer Implementation

```python
class JsonRenderer(OutputRenderer):
    """Renders output as JSON for machine consumption."""

    def render_simple(self, data: dict[str, Any]) -> None:
        emit_json(data)  # ← Goes to stdout

    def render_status(self, status_data: Any) -> None:
        from erk.cli.json_schemas import status_data_to_pydantic

        # Convert to Pydantic model for validation
        pydantic_model = status_data_to_pydantic(status_data)
        # Convert to dict and emit
        dict_data = pydantic_model.model_dump(mode="json")
        emit_json(dict_data)
```

**Characteristics:**

- Uses `emit_json()` → `machine_output()` (stdout)
- Converts data to Pydantic models for validation
- Handles serialization automatically

#### Factory Function

```python
def get_renderer(format: str) -> OutputRenderer:
    """Factory function to get appropriate renderer.

    Args:
        format: Output format ("text" or "json")

    Returns:
        Appropriate renderer instance
    """
    if format == "json":
        return JsonRenderer()
    return TextRenderer()
```

**Usage in commands:**

```python
renderer = get_renderer(format)
renderer.render_status(status_data)
```

**Reference:** `src/erk/cli/rendering.py:14-159`

### Step-by-Step Implementation

#### 1. Define Complex Pydantic Schemas

**File:** `src/erk/cli/json_schemas.py`

```python
class StatusWorktreeInfo(BaseModel):
    """Worktree information in status command output."""

    model_config = ConfigDict(strict=True)

    name: str
    path: str
    branch: str | None
    is_root: bool


class StatusPlanInfo(BaseModel):
    """Plan information in status command output."""

    model_config = ConfigDict(strict=True)

    exists: bool
    objective: str | None
    progress_summary: str | None


class StatusCommandResponse(BaseModel):
    """JSON response schema for the `erk status --format json` command."""

    model_config = ConfigDict(strict=True)

    worktree_info: StatusWorktreeInfo
    plan: StatusPlanInfo | None
    stack: StatusStackInfo | None
    pr_status: StatusPRInfo | None
    git_status: StatusGitInfo
    related_worktrees: list[StatusRelatedWorktree]
```

**Schema characteristics:**

- **Deeply nested** - Multiple levels of nested models
- **Optional sections** - Many `| None` fields for sections that may not exist
- **Lists of nested models** - `list[StatusRelatedWorktree]`
- **Field constraints** - `Field(..., pattern="^(open|merged|closed)$")`

**Reference:** `src/erk/cli/json_schemas.py:112-240`

#### 2. Add `--format` Choice Parameter

```python
@click.command("status")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (text or json)",
)
@json_error_boundary  # ← Add decorator for structured error handling
@click.pass_obj
def status_cmd(ctx: ErkContext, format: str) -> None:
    """Show comprehensive status of current worktree."""
```

**Key differences from Pattern 1/2:**

- Use `--format` with `Choice`, not `--json` boolean flag
- Add `@json_error_boundary` decorator
- Decorator goes before `@click.pass_obj`

**Decorator order is critical:**

```python
@click.command("status")
@click.option("--format", ...)  # ← Define parameter first
@json_error_boundary            # ← Then error boundary
@click.pass_obj                 # ← Then pass context
def status_cmd(...):
```

**Reference:** `src/erk/cli/commands/status.py:18-27`

#### 3. Implement Command with Renderer

```python
def status_cmd(ctx: ErkContext, format: str) -> None:
    """Show comprehensive status of current worktree."""
    # 1. Collect data (same for all formats)
    repo = discover_repo_context(ctx, ctx.cwd)
    current_worktree_path = find_current_worktree_path(ctx, repo)

    collectors = [
        GitStatusCollector(),
        GraphiteStackCollector(),
        GitHubPRCollector(),
        PlanFileCollector(),
    ]

    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())
    status = orchestrator.collect_status(ctx, current_worktree_path, repo.root)

    # 2. Get appropriate renderer
    renderer = get_renderer(format)

    # 3. Render output (format-specific)
    renderer.render_status(status)
```

**Key patterns:**

- **Single data collection path** - Business logic unchanged by format
- **Factory function** - `get_renderer(format)` returns appropriate renderer
- **Polymorphic rendering** - Same method call, different implementations

**Reference:** `src/erk/cli/commands/status.py:27-73`

#### 4. Implement Conversion Function (If Needed)

If your data structure is not a Pydantic model, create a conversion function:

```python
def status_data_to_pydantic(status_data: StatusData) -> StatusCommandResponse:
    """Convert StatusData dataclass to Pydantic model for validation.

    Args:
        status_data: StatusData object from status collectors

    Returns:
        StatusCommandResponse Pydantic model with validated structure
    """
    # Convert worktree_info
    worktree_info = StatusWorktreeInfo(
        name=status_data.worktree_info.name,
        path=str(status_data.worktree_info.path),  # ← Path to str
        branch=status_data.worktree_info.branch,
        is_root=status_data.worktree_info.is_root,
    )

    # Convert plan (optional section)
    plan: StatusPlanInfo | None = None
    if status_data.plan:
        plan = StatusPlanInfo(
            exists=status_data.plan.exists,
            objective=status_data.plan.summary,
            progress_summary=status_data.plan.progress_summary,
        )

    # Build top-level response
    return StatusCommandResponse(
        worktree_info=worktree_info,
        plan=plan,
        stack=stack,
        pr_status=pr_status,
        git_status=git_status,
        related_worktrees=related_worktrees,
    )
```

**When to use conversion functions:**

- ✅ Data comes from dataclasses or other non-Pydantic structures
- ✅ Complex mapping logic between internal and external representations
- ✅ Need to preserve existing internal data structures

**Reference:** `src/erk/cli/json_schemas.py:275-364`

### Testing Pattern 3

**Minimum 3+ tests required:**

1. **Happy path text output** - Verify text rendering works
2. **Happy path JSON output** - Verify JSON structure
3. **Schema validation** - Test conversion function
4. **Error handling** - Verify `@json_error_boundary` works

**Example tests:**

```python
def test_status_text_format(erk_inmem_env):
    """Test status command with text format."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(status_cmd, ["--format", "text"], obj=ctx)

        assert result.exit_code == 0
        assert "Worktree:" in result.output  # Text format indicators

def test_status_json_format(erk_inmem_env):
    """Test status command with JSON format."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(status_cmd, ["--format", "json"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)

        # Validate top-level structure
        assert "worktree_info" in data
        assert "git_status" in data
        assert "plan" in data

        # Validate nested structure
        assert data["worktree_info"]["name"] == env.worktree_name
        assert data["worktree_info"]["path"] == str(env.worktree_path)

def test_status_json_error_handling(erk_inmem_env):
    """Test that errors in JSON mode output structured errors."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create scenario that causes error
        ctx = env.build_context(invalid_state=True)
        result = runner.invoke(status_cmd, ["--format", "json"], obj=ctx)

        assert result.exit_code != 0
        data = json.loads(result.output)

        # Verify error structure
        assert "error" in data
        assert "error_type" in data
        assert "exit_code" in data

def test_status_data_to_pydantic_conversion():
    """Test conversion from StatusData to Pydantic model."""
    from erk.cli.json_schemas import status_data_to_pydantic
    from erk.status.models.status_data import StatusData, WorktreeInfo

    # Create test StatusData
    status_data = StatusData(
        worktree_info=WorktreeInfo(
            name="feature",
            path=Path("/repo/worktrees/feature"),
            branch="feature-branch",
            is_root=False,
        ),
        plan=None,
        stack_position=None,
        pr_status=None,
        git_status=None,
        related_worktrees=[],
    )

    # Convert to Pydantic
    pydantic_model = status_data_to_pydantic(status_data)

    # Validate conversion
    assert pydantic_model.worktree_info.name == "feature"
    assert pydantic_model.worktree_info.path == "/repo/worktrees/feature"
    assert pydantic_model.plan is None
```

## Testing Patterns

### Minimum Test Requirements

**All patterns require minimum 3 tests:**

1. **Happy path** - Valid input, successful output
2. **Edge case** - Boundary conditions, special values
3. **Schema validation** - Pydantic model validates correctly

**Pattern 2 (Complex) requires 5+ tests:**

- Add tests for optional sections, empty collections

**Pattern 3 (Renderer) requires additional tests:**

- Conversion function tests
- Error boundary tests

### Test Fixtures

**Use `erk_inmem_env()` for test environment:**

```python
from click.testing import CliRunner

def test_my_command(erk_inmem_env):
    """Test command with in-memory environment."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(my_command, ["--json"], obj=ctx)

        assert result.exit_code == 0
```

**Fixture provides:**

- `env.cwd` - Current working directory
- `env.worktree_name` - Test worktree name
- `env.worktree_path` - Test worktree path
- `env.build_context()` - Creates test ErkContext

### JSON Parsing and Validation

**Standard pattern:**

```python
import json

def test_json_output(erk_inmem_env):
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(command, ["--json"], obj=ctx)

        # 1. Check exit code
        assert result.exit_code == 0

        # 2. Parse JSON
        data = json.loads(result.output)

        # 3. Validate structure
        assert "field1" in data
        assert data["field2"] == expected_value

        # 4. Validate types
        assert isinstance(data["field3"], str)
        assert isinstance(data["field4"], list)
```

### Schema Validation Tests

**Test Pydantic models directly:**

```python
from pydantic import ValidationError
import pytest

def test_schema_validation():
    """Test that response schema validates correctly."""
    from erk.cli.json_schemas import MyCommandResponse

    # Test valid data
    response = MyCommandResponse(
        field1="value",
        field2=42,
    )
    assert response.field1 == "value"

    # Test invalid data - missing required field
    with pytest.raises(ValidationError):
        MyCommandResponse(field1="value")  # Missing field2

    # Test invalid data - wrong type
    with pytest.raises(ValidationError):
        MyCommandResponse(field1="value", field2="not an int")

    # Test field constraints
    with pytest.raises(ValidationError):
        MyCommandResponse(
            field1="value",
            field2=42,
            status="invalid",  # Must match pattern
        )
```

### Test Organization

**Test file structure:**

```python
# tests/cli/test_mycommand.py

"""Tests for mycommand CLI command."""

import json
import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from erk.cli.commands.mycommand import mycommand_cmd
from erk.cli.json_schemas import MyCommandResponse


class TestMyCommandText:
    """Tests for text output format."""

    def test_text_output_happy_path(self, erk_inmem_env):
        """Test text output with valid input."""
        ...

    def test_text_output_edge_case(self, erk_inmem_env):
        """Test text output with edge case."""
        ...


class TestMyCommandJson:
    """Tests for JSON output format."""

    def test_json_output_happy_path(self, erk_inmem_env):
        """Test JSON output with valid input."""
        ...

    def test_json_output_edge_case(self, erk_inmem_env):
        """Test JSON output with special values."""
        ...

    def test_json_optional_fields(self, erk_inmem_env):
        """Test JSON output with optional fields."""
        ...


class TestMyCommandSchema:
    """Tests for Pydantic schema validation."""

    def test_schema_validates_correct_data(self):
        """Test schema accepts valid data."""
        ...

    def test_schema_rejects_invalid_data(self):
        """Test schema rejects invalid data."""
        ...

    def test_schema_field_constraints(self):
        """Test schema field constraints."""
        ...
```

## Common Patterns & Conventions

### Flag Naming

**Use `--json` for boolean flag:**

```python
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
def command(output_json: bool):
    if output_json:
        ...
```

**Use `--format` for choice parameter:**

```python
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def command(format: str):
    renderer = get_renderer(format)
    ...
```

**Never mix the two:**

- Pattern 1 & 2: `--json` boolean flag
- Pattern 3: `--format` choice parameter

### Output Routing

**Always use output abstraction:**

```python
from erk.cli.output import user_output, machine_output
from erk.cli.json_output import emit_json

# ✅ CORRECT: User messages to stderr
user_output("✓ Created worktree")

# ✅ CORRECT: JSON to stdout (via emit_json)
emit_json(data)

# ✅ CORRECT: Script data to stdout
machine_output(str(path))

# ❌ WRONG: Direct print() or click.echo()
print("Created worktree")  # Don't use print()
click.echo(json_str)  # Don't use click.echo() for JSON
```

### Pydantic Model Conversion

**Always use `mode="json"` when converting:**

```python
# ✅ CORRECT: mode="json" handles Path/datetime
response = MyResponse(name="test", path=str(path))
emit_json(response.model_dump(mode="json"))

# ❌ WRONG: Missing mode="json"
emit_json(response.model_dump())  # May not serialize correctly

# ❌ WRONG: Passing model directly
emit_json(response)  # Type error
```

**Why `mode="json"` matters:**

- Ensures Pydantic serializes special types (Path, datetime)
- Even though we convert Path to str in schemas, `mode="json"` is defensive
- Consistent with Pydantic best practices

### Path Handling

**Convert Path to str at construction time:**

```python
# ✅ CORRECT: Convert when constructing model
response = WorktreeInfo(
    name=wt.name,
    path=str(wt.path),  # ← Explicit conversion
    branch=wt.branch,
)

# ❌ WRONG: Path type in schema
class WorktreeInfo(BaseModel):
    path: Path  # Don't use Path in schemas
```

### Optional Fields

**Use `| None` for optional fields:**

```python
# ✅ CORRECT: Python 3.13+ union syntax
class MyResponse(BaseModel):
    required_field: str
    optional_field: str | None
    optional_number: int | None

# ❌ WRONG: Old typing syntax
from typing import Optional
class MyResponse(BaseModel):
    optional_field: Optional[str]  # Don't use Optional
```

**Handle optional sections conditionally:**

```python
# ✅ CORRECT: Set entire section to None if not available
plan_info = None
if status_data.plan:
    plan_info = PlanInfo(...)

response = StatusResponse(
    worktree_info=worktree_info,
    plan=plan_info,  # ← Can be None
)

# ❌ WRONG: Constructing model with None values for required fields
plan_info = PlanInfo(
    exists=False,
    objective=None,  # Type error if objective is required
)
```

### Error Handling

**Pattern 1 & 2: Let exceptions bubble:**

```python
@click.command()
@click.option("--json", "output_json", is_flag=True)
@click.pass_obj
def command(ctx: ErkContext, output_json: bool):
    # No try/except - let exceptions bubble to CLI layer
    result = operation_that_may_fail()

    if output_json:
        emit_json(response.model_dump(mode="json"))
    else:
        user_output(result)
```

**Pattern 3: Use `@json_error_boundary`:**

```python
@click.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@json_error_boundary  # ← Catches exceptions in JSON mode
@click.pass_obj
def command(ctx: ErkContext, format: str):
    # Errors automatically converted to JSON errors if format == "json"
    result = operation_that_may_fail()

    renderer = get_renderer(format)
    renderer.render(result)
```

## Common Pitfalls

### Pitfall 1: Passing Pydantic Model Directly to emit_json()

**Problem:**

```python
# ❌ WRONG: emit_json() expects dict, not BaseModel
response = CurrentCommandResponse(name="feature", path="/path", is_root=False)
emit_json(response)  # Type error!
```

**Solution:**

```python
# ✅ CORRECT: Convert to dict first
response = CurrentCommandResponse(name="feature", path="/path", is_root=False)
emit_json(response.model_dump(mode="json"))
```

**Why it matters:** `emit_json()` has a dict-only interface to keep the contract simple and explicit.

### Pitfall 2: Using Path Type in Schemas

**Problem:**

```python
# ❌ WRONG: Path type in schema
class WorktreeInfo(BaseModel):
    name: str
    path: Path  # Don't use Path type
    branch: str | None
```

**Solution:**

```python
# ✅ CORRECT: Use str in schema, convert at construction
class WorktreeInfo(BaseModel):
    name: str
    path: str  # Use str, not Path
    branch: str | None

# Convert Path to str when constructing
info = WorktreeInfo(
    name=wt.name,
    path=str(wt.path),  # ← Explicit conversion
    branch=wt.branch,
)
```

**Why it matters:** Keeps schemas as primitive types, matches JSON's native string type, follows LBYL principle.

### Pitfall 3: Missing `mode="json"` in model_dump()

**Problem:**

```python
# ❌ WRONG: Missing mode="json"
response = MyResponse(...)
emit_json(response.model_dump())  # May not serialize correctly
```

**Solution:**

```python
# ✅ CORRECT: Always use mode="json"
response = MyResponse(...)
emit_json(response.model_dump(mode="json"))
```

**Why it matters:** Ensures Pydantic serializes special types correctly (Path, datetime, etc.).

### Pitfall 4: Skipping Schema Validation Tests

**Problem:**

```python
# ❌ WRONG: Only testing command output, not schema validation
def test_command_json(erk_inmem_env):
    result = runner.invoke(command, ["--json"])
    assert result.exit_code == 0
    # No schema validation!
```

**Solution:**

```python
# ✅ CORRECT: Test schema validation separately
def test_command_json(erk_inmem_env):
    """Test command JSON output."""
    result = runner.invoke(command, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "field1" in data

def test_schema_validation():
    """Test schema validates correctly."""
    from erk.cli.json_schemas import MyResponse

    # Test valid data
    response = MyResponse(field1="value", field2=42)
    assert response.field1 == "value"

    # Test invalid data
    with pytest.raises(ValidationError):
        MyResponse(field1="value")  # Missing field2
```

**Why it matters:** Schema validation tests ensure the structure is correct even if command logic changes.

### Pitfall 5: Using `--json` and `--format` Interchangeably

**Problem:**

```python
# ❌ WRONG: Mixing flag types
@click.option("--json", is_flag=True)
def simple_command(json: bool):
    ...

@click.option("--json", type=click.Choice(["text", "json"]))
def complex_command(json: str):
    ...
```

**Solution:**

```python
# ✅ CORRECT: Use --json for Patterns 1 & 2
@click.option("--json", "output_json", is_flag=True)
def simple_command(output_json: bool):
    if output_json:
        ...

# ✅ CORRECT: Use --format for Pattern 3
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def complex_command(format: str):
    renderer = get_renderer(format)
    ...
```

**Why it matters:** Consistent flag naming across commands. `--json` is boolean, `--format` is choice.

### Pitfall 6: Forgetting `@json_error_boundary` Decorator

**Problem:**

```python
# ❌ WRONG: No error boundary for renderer-based command
@click.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@click.pass_obj
def status_cmd(ctx: ErkContext, format: str):
    # Errors will not be caught in JSON mode
    ...
```

**Solution:**

```python
# ✅ CORRECT: Add @json_error_boundary before @click.pass_obj
@click.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@json_error_boundary  # ← Add decorator
@click.pass_obj
def status_cmd(ctx: ErkContext, format: str):
    # Errors automatically converted to JSON errors if format == "json"
    ...
```

**Why it matters:** Provides structured error output in JSON mode. Without it, errors are raised as normal exceptions.

### Pitfall 7: Using print() or click.echo() Directly

**Problem:**

```python
# ❌ WRONG: Direct print() or click.echo()
def my_command(output_json: bool):
    if output_json:
        print(json_str)  # Wrong stream
    else:
        print("Status message")  # Wrong stream
```

**Solution:**

```python
# ✅ CORRECT: Use output abstraction
from erk.cli.output import user_output
from erk.cli.json_output import emit_json

def my_command(output_json: bool):
    if output_json:
        emit_json(data)  # → stdout via machine_output()
    else:
        user_output("Status message")  # → stderr
```

**Why it matters:** Stream separation enables shell script integration without interference.

### Pitfall 8: Constructing Models with None for Required Fields

**Problem:**

```python
# ❌ WRONG: Constructing model with None for required fields
plan_info = PlanInfo(
    exists=False,
    objective=None,  # Type error if objective is required (not str | None)
    progress_summary=None,
)
```

**Solution:**

```python
# ✅ CORRECT: Set entire section to None if not available
plan_info = None
if status_data.plan:
    plan_info = PlanInfo(
        exists=status_data.plan.exists,
        objective=status_data.plan.objective,
        progress_summary=status_data.plan.progress_summary,
    )

response = StatusResponse(
    plan=plan_info,  # ← Can be None (declared as PlanInfo | None)
)
```

**Why it matters:** Pydantic will raise validation errors if required fields are None. Check if the entire section should be None instead.

## Reference Files

### Infrastructure Files

**Core JSON utilities:**

- `src/erk/cli/json_output.py` - JSON output functions and decorators
  - `emit_json()` (lines 61-80) - Main JSON output function
  - `_serialize_for_json()` (lines 32-58) - Special type handling
  - `@json_error_boundary` (lines 106-148) - Error decorator
  - `ErrorResponse` (lines 16-29) - Error schema

**Output abstraction:**

- `src/erk/cli/output.py` - Stream routing utilities
  - `user_output()` (lines 8-24) - User messages to stderr
  - `machine_output()` (lines 27-43) - Structured data to stdout

**Renderer framework:**

- `src/erk/cli/rendering.py` - Output rendering abstraction
  - `OutputRenderer` ABC (lines 15-54) - Base renderer interface
  - `TextRenderer` (lines 57-99) - Text output implementation
  - `JsonRenderer` (lines 102-141) - JSON output implementation
  - `get_renderer()` (lines 144-159) - Factory function

**Pydantic schemas:**

- `src/erk/cli/json_schemas.py` - Response schemas
  - `CurrentCommandResponse` (lines 37-50) - Simple schema example
  - `ConfigListResponse` (lines 96-109) - Complex nested schema
  - `StatusCommandResponse` (lines 218-239) - Deeply nested schema
  - `status_data_to_pydantic()` (lines 275-364) - Conversion function

### Example Implementations

**Pattern 1: Simple Commands**

- `src/erk/cli/commands/current.py` - Simple single-object response
  - Command definition (lines 14-22) - `--json` flag
  - Business logic (lines 23-41) - Data collection
  - Conditional output (lines 43-52) - JSON vs text

**Pattern 2: Complex Commands**

- `src/erk/cli/commands/config.py` - Complex nested structures
  - Command definition (lines 64-67) - `--json` flag
  - Nested model construction (lines 69-96) - Building response
  - Optional section handling (lines 73-90) - Conditional sections

**Pattern 3: Renderer-Based**

- `src/erk/cli/commands/status.py` - Renderer-based output
  - Command definition (lines 18-27) - `--format` choice and `@json_error_boundary`
  - Data collection (lines 37-69) - Status orchestration
  - Renderer usage (lines 71-73) - `get_renderer()` and `render_status()`

### Test Files

**JSON output tests:**

- `tests/cli/test_json_output.py` - Tests for emit_json() and serialization

**Renderer tests:**

- `tests/cli/test_rendering.py` - Tests for renderer framework

**Command tests:**

- `tests/cli/test_current.py` - Pattern 1 test examples
- `tests/cli/test_config.py` - Pattern 2 test examples
- `tests/cli/test_status.py` - Pattern 3 test examples

### Documentation

**CLI module documentation:**

- `src/erk/cli/AGENTS.md` - Pydantic serialization patterns and design rationale
- `src/erk/cli/CLAUDE.md` - Points to AGENTS.md for CLI module docs

**Project coding standards:**

- `../../../AGENTS.md` (root) - Top 6 critical rules
- `dignified-python` skill - Complete Python standards
- `../testing.md` - Testing architecture and patterns

---

## Summary

This guide covered three patterns for adding JSON output to CLI commands:

1. **Pattern 1: Simple Commands** - Boolean `--json` flag, single object response
2. **Pattern 2: Complex Commands** - Boolean `--json` flag, nested structures
3. **Pattern 3: Renderer-Based** - `--format` choice parameter, renderer abstraction

**Key principles:**

- **Stream separation** - `user_output()` (stderr) for humans, `machine_output()` (stdout) for machines
- **Dict-only interface** - `emit_json()` accepts dicts, convert Pydantic models first
- **Path as str** - Always use `str` in schemas, convert at construction
- **Strict validation** - Always use `ConfigDict(strict=True)` in Pydantic models
- **Test coverage** - Minimum 3 tests per JSON feature (happy path, edge case, schema validation)

**Choose the right pattern:**

- Use Pattern 1 for simple single-object responses
- Use Pattern 2 for complex nested structures
- Use Pattern 3 when you already have structured data and renderers

**Always remember:**

- Convert Pydantic models with `.model_dump(mode="json")` before `emit_json()`
- Use output abstraction (`user_output()`, `machine_output()`, `emit_json()`)
- Write tests for JSON structure and schema validation
- Follow the checklist at the top of this guide
