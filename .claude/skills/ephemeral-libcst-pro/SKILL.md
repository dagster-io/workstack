---
name: ephemeral-libcst-pro
description: This skill should be used when performing Python refactoring across multiple files using LibCST for precise AST transformations without creating permanent codemods.
version: 2.1.0
tags:
  - refactoring
  - python
  - ast
  - libcst
  - ephemeral
  - codemods
---

# Ephemeral LibCST Pro: Surgical Python Refactoring

## Philosophy

This skill teaches battle-tested patterns for creating **throwaway LibCST scripts** that perform precise Python refactoring across multiple files. These are surgical, one-time transformations—not permanent codemods.

**The Problem This Solves:**

- **Regex-based refactoring** is too fragile (breaks on edge cases, destroys formatting)
- **Manual refactoring** is tedious and error-prone across hundreds of files
- **Permanent codemods** are too heavyweight for one-time transformations

**LibCST gives you:**

- Parse-preserving AST transformations (keeps formatting, comments, spacing)
- Type-safe node manipulation
- Matcher-based pattern recognition
- Surgical precision for complex Python refactoring

## When to Activate This Skill

Use this skill when:

- ✅ Refactoring function/method signatures across many files
- ✅ Renaming symbols with context-aware logic (not simple find-replace)
- ✅ Transforming imports (merging, splitting, renaming)
- ✅ Modifying decorators or annotations systematically
- ✅ Converting between patterns (e.g., dataclass fields to attrs)
- ✅ Need to preserve formatting, comments, and whitespace exactly

**Don't use this skill when:**

- ❌ Simple find-replace across files (use sed/grep/IDE refactoring)
- ❌ Building a permanent codemod library (different design patterns)
- ❌ One-off change to a single file (just edit it manually)

## 6 Critical Success Principles

### 1. Visualize FIRST, Code SECOND

**Always visualize the LibCST tree before writing transformation logic.**

LibCST's structure is verbose and counterintuitive. Seeing the actual tree prevents 90% of errors.

**Fastest way: Use the CLI tool**

```bash
# Visualize any Python file's CST
python -m libcst.tool print file.py

# Show whitespace nodes
python -m libcst.tool print file.py --show-whitespace

# Show default values
python -m libcst.tool print file.py --show-defaults
```

**Or use Python:**

```python
import libcst as cst

code = '''
def foo():
    assert bar, "message"
'''

tree = cst.parse_module(code)
print(tree)
```

**Output shows:**

```
Module(
    body=[
        FunctionDef(
            name=Name("foo"),
            body=IndentedBlock(
                body=[
                    SimpleStatementLine(
                        body=[Assert(...)]  # ← Assert is INSIDE SimpleStatementLine!
                    )
                ]
            )
        )
    ]
)
```

**Key insight:** Small statements like `Assert`, `Expr`, `Pass` live INSIDE `SimpleStatementLine`. Compound statements like `If`, `For` are direct children of `IndentedBlock`.

### 2. Use Matchers, Not isinstance

**Matchers are cleaner and more maintainable than isinstance chains.**

```python
from libcst import matchers as m

# ❌ WRONG: Verbose isinstance chain
if (isinstance(node, cst.Call) and
    isinstance(node.func, cst.Name) and
    node.func.value == "old_function"):
    ...

# ✅ CORRECT: Clean matcher
if m.matches(node, m.Call(func=m.Name("old_function"))):
    ...
```

**Matchers support:**

- Wildcards: `m.DoNotCare()` matches anything
- Logical operators: `m.OneOf()`, `m.AllOf()`
- Decorator syntax for cleaner code (see references/patterns.md)

**Type-checker friendly: Use `ensure_type()`**

```python
# Combine matchers with ensure_type() for type-safe code
if m.matches(node, m.Name()):
    name_value = cst.ensure_type(node, cst.Name).value
    # Type checker knows node is cst.Name here
```

### 3. ALWAYS Return updated_node, Not original_node

**By the time `leave_*` is called, child nodes are already transformed.**

Returning `original_node` discards all child modifications.

```python
# ❌ WRONG: Discards child transformations
def leave_FunctionDef(self, original_node, updated_node):
    if should_transform(original_node):
        return updated_node.with_changes(name=new_name)
    return original_node  # ← BUG: Loses child changes!

# ✅ CORRECT: Preserves child transformations
def leave_FunctionDef(self, original_node, updated_node):
    if should_transform(original_node):
        return updated_node.with_changes(name=new_name)
    return updated_node  # ← Keeps child changes
```

**Why this matters: Nested transformations**

```python
# Input code: some_func(1, 2, other_func(3))

class RenameTransformer(cst.CSTTransformer):
    def leave_Call(self, original_node, updated_node):
        if m.matches(updated_node.func, m.Name()):
            new_name = "renamed_" + updated_node.func.value
            return updated_node.with_changes(func=cst.Name(new_name))
        return updated_node  # ← CRITICAL: Return updated_node!

# Output: renamed_some_func(1, 2, renamed_other_func(3))
# Both outer AND nested calls renamed!

# If you return original_node instead:
# Output: renamed_some_func(1, 2, other_func(3))
# Nested call NOT renamed! Child transformation lost!
```

**Rule:** Always return `updated_node` (possibly with modifications), never `original_node`.

### 4. Handle SimpleStatementLine vs IndentedBlock Correctly

**Statement type boundaries are critical for transformations.**

Small statements (Assert, Expr, Pass) cannot be directly replaced with compound statements (If, For).

```python
# ❌ WRONG: Can't replace Assert with If directly
def leave_Assert(self, original_node, updated_node):
    return cst.If(...)  # ← BUG: Type mismatch!

# ✅ CORRECT: Work at SimpleStatementLine level
def leave_SimpleStatementLine(self, original_node, updated_node):
    if m.matches(updated_node.body[0], m.Assert(...)):
        return cst.If(...)  # ← Replaces the entire line
    return updated_node
```

**Or use `FlattenSentinel` to insert multiple statements:**

```python
from libcst import FlattenSentinel

def leave_SimpleStatementLine(self, original_node, updated_node):
    if m.matches(updated_node.body[0], m.Assert(...)):
        return FlattenSentinel([
            cst.SimpleStatementLine([cst.Expr(...)]),
            cst.If(...)
        ])
    return updated_node
```

### 5. Use config_for_parsing for Generated Code

**Manually constructed nodes often have incorrect whitespace.**

Parsing from strings preserves proper formatting.

```python
# ❌ WRONG: Manual construction = spacing issues
new_call = cst.Call(
    func=cst.Name("new_func"),
    args=[cst.Arg(cst.Name("x"))]
)

# ✅ CORRECT: Parse from string = correct spacing
module = cst.parse_module("")
new_call = cst.parse_expression(
    "new_func(x)",
    config=module.config_for_parsing
)
```

**Always use `module.config_for_parsing` to match the original file's style.**

### 6. Use Template Functions for Complex Code Generation

**For code with variable parts, use template functions with placeholders.**

LibCST provides `parse_template_*` functions that work like f-strings for AST nodes.

```python
from libcst.helpers import parse_template_statement, parse_template_expression

# ❌ WRONG: Manual construction is verbose and error-prone
assert_node = cst.Assert(
    test=cst.Comparison(
        left=cst.Name("x"),
        comparisons=[cst.ComparisonTarget(
            operator=cst.GreaterThan(),
            comparator=cst.Integer("0")
        )]
    ),
    msg=cst.SimpleString('"Value must be positive"')
)

# ✅ CORRECT: Template with variable substitution
module = cst.parse_module("")
assert_node = parse_template_statement(
    "assert {var} > 0, {msg}",
    var=cst.Name("x"),
    msg=cst.SimpleString('"Value must be positive"'),
    config=module.config_for_parsing
)

# ✅ Also works for expressions
new_expr = parse_template_expression(
    "{obj}.{method}({arg})",
    obj=cst.Name("foo"),
    method=cst.Name("bar"),
    arg=cst.Name("baz"),
    config=module.config_for_parsing
)
```

**Use templates when:**

- Generating complex statements with variable parts
- Mixing literal code structure with dynamic values
- Need clean, readable code generation

## Battle-Tested Script Template

Use this template for ephemeral refactoring scripts:

```python
#!/usr/bin/env python3
"""
One-line description of transformation.

Example:
  python refactor_script.py path/to/file.py --dry-run
  python refactor_script.py src/**/*.py
"""
import sys
from pathlib import Path
import libcst as cst
from libcst import matchers as m
from libcst import RemovalSentinel, FlattenSentinel

class MyTransformer(cst.CSTTransformer):
    """Transform description."""

    def __init__(self):
        super().__init__()
        self.changes_made = 0

    def leave_FunctionDef(self, original_node, updated_node):
        # Example: Rename function
        if m.matches(updated_node, m.FunctionDef(name=m.Name("old_name"))):
            self.changes_made += 1
            return updated_node.with_changes(
                name=cst.Name("new_name")
            )
        return updated_node

    # To remove nodes: from libcst import RemoveFromParent
    # return RemoveFromParent()

    # To insert multiple statements:
    # return FlattenSentinel([statement1, statement2])

def transform_file(file_path: Path, dry_run: bool = False) -> bool:
    """Transform a single file. Returns True if changes made."""
    if not file_path.exists():
        print(f"Skipping {file_path}: does not exist")
        return False

    source = file_path.read_text(encoding="utf-8")

    try:
        tree = cst.parse_module(source)
    except Exception as e:
        print(f"Parse error in {file_path}: {e}")
        return False

    transformer = MyTransformer()
    new_tree = tree.visit(transformer)

    if transformer.changes_made == 0:
        return False

    if dry_run:
        print(f"[DRY RUN] Would modify {file_path}: {transformer.changes_made} changes")
        return True

    file_path.write_text(new_tree.code, encoding="utf-8")
    print(f"✓ Modified {file_path}: {transformer.changes_made} changes")
    return True

def main():
    dry_run = "--dry-run" in sys.argv
    paths = [arg for arg in sys.argv[1:] if arg != "--dry-run"]

    if not paths:
        print(__doc__)
        sys.exit(1)

    total_modified = 0
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            if transform_file(path, dry_run):
                total_modified += 1
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                if transform_file(py_file, dry_run):
                    total_modified += 1

    print(f"\n{'[DRY RUN] Would modify' if dry_run else 'Modified'} {total_modified} files")

if __name__ == "__main__":
    main()
```

## Pre-Flight Checklist

Before running a LibCST script on your codebase:

1. **✅ Visualize the tree structure** for representative code samples
2. **✅ Test on ONE file first** to validate transformation logic
3. **✅ Run in dry-run mode** to preview changes
4. **✅ Commit current work** so you can easily revert
5. **✅ Check path.exists() before operations** (dignified-python standard)
6. **✅ Use absolute imports** in the script itself

## Integration with Claude Code

When Claude Code activates this skill:

1. **Understand the transformation** - Ask clarifying questions about edge cases
2. **Visualize first** - Show the LibCST tree structure for sample code
3. **Draft the transformer** - Write the transformation logic using matchers
4. **Create the script** - Use the battle-tested template above
5. **Test iteratively** - Start with one file, then expand
6. **Provide recovery commands** - Include git reset instructions

**Always provide:**

- Clear docstring explaining the transformation
- Dry-run mode for safety
- Change counters for progress tracking
- Git recovery commands in comments

## Reference

For detailed transformation patterns, gotchas, debugging techniques, and execution strategies, see:

- **[references/patterns.md](references/patterns.md)** - 11 common patterns, 5 critical gotchas, 4 debugging techniques, advanced scope-aware refactoring

Load these references when you need:

- Specific transformation examples (rename, imports, decorators, node removal, insertion)
- Solutions to common errors (semicolons, commas, whitespace)
- Advanced patterns (matcher decorators, complex matching, template generation)
- Scope-aware refactoring (ScopeProvider, QualifiedNameProvider)
- Official helper utilities (import management, type narrowing)
- Execution strategies (progressive rollout, git safety)
