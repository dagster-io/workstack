# LibCST Transformation Patterns & Gotchas

This reference provides detailed patterns, solutions to common pitfalls, debugging techniques, and execution strategies for LibCST-based refactoring.

## 11 Common Transformation Patterns

### Pattern 1: Rename Function/Method

**Goal:** Rename a function or method across files.

```python
from libcst import matchers as m

class RenameFunctionTransformer(cst.CSTTransformer):
    def __init__(self, old_name: str, new_name: str):
        super().__init__()
        self.old_name = old_name
        self.new_name = new_name
        self.changes_made = 0

    def leave_FunctionDef(self, original_node, updated_node):
        if m.matches(updated_node, m.FunctionDef(name=m.Name(self.old_name))):
            self.changes_made += 1
            return updated_node.with_changes(name=cst.Name(self.new_name))
        return updated_node

    def leave_Call(self, original_node, updated_node):
        # Also rename call sites
        if m.matches(updated_node.func, m.Name(self.old_name)):
            self.changes_made += 1
            return updated_node.with_changes(func=cst.Name(self.new_name))
        return updated_node
```

**Key points:**

- Transform both definitions AND call sites
- Use matchers for clean matching logic
- Track changes for progress reporting

### Pattern 2: Add/Modify Function Arguments

**Goal:** Add a new argument to function signatures and update call sites.

```python
from libcst import matchers as m

class AddArgumentTransformer(cst.CSTTransformer):
    def __init__(self, function_name: str, new_arg_name: str, default_value: str):
        super().__init__()
        self.function_name = function_name
        self.new_arg_name = new_arg_name
        self.default_value = default_value
        self.changes_made = 0

    def leave_FunctionDef(self, original_node, updated_node):
        if not m.matches(updated_node, m.FunctionDef(name=m.Name(self.function_name))):
            return updated_node

        # Parse the new parameter with default
        module = cst.parse_module("")
        new_param = cst.Param(
            name=cst.Name(self.new_arg_name),
            default=cst.parse_expression(self.default_value, config=module.config_for_parsing)
        )

        # Add to parameters
        new_params = list(updated_node.params.params) + [new_param]
        self.changes_made += 1

        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params)
        )
```

**Key points:**

- Use `config_for_parsing` for default values to get correct spacing
- Handle params as a list (immutable, so create new list)
- Consider whether to update call sites (depends on default value)

### Pattern 3: Update Imports

**Goal:** Rename imports or reorganize them.

```python
from libcst import matchers as m

class RenameImportTransformer(cst.CSTTransformer):
    def __init__(self, old_module: str, new_module: str):
        super().__init__()
        self.old_module = old_module
        self.new_module = new_module
        self.changes_made = 0

    def leave_Import(self, original_node, updated_node):
        # Handle: import old_module
        new_names = []
        for name in updated_node.names:
            if isinstance(name.name, cst.Name) and name.name.value == self.old_module:
                self.changes_made += 1
                new_names.append(name.with_changes(name=cst.Name(self.new_module)))
            else:
                new_names.append(name)
        return updated_node.with_changes(names=new_names)

    def leave_ImportFrom(self, original_node, updated_node):
        # Handle: from old_module import ...
        if updated_node.module and m.matches(updated_node.module, m.Name(self.old_module)):
            self.changes_made += 1
            return updated_node.with_changes(module=cst.Name(self.new_module))
        return updated_node
```

**Key points:**

- Handle both `import` and `from ... import` forms
- Preserve import aliases and relative imports
- Consider updating usage sites if module name changes

### Pattern 4: Modify String Literals

**Goal:** Transform string literals matching a pattern.

```python
from libcst import matchers as m

class UpdateStringLiteralsTransformer(cst.CSTTransformer):
    def __init__(self, old_prefix: str, new_prefix: str):
        super().__init__()
        self.old_prefix = old_prefix
        self.new_prefix = new_prefix
        self.changes_made = 0

    def leave_SimpleString(self, original_node, updated_node):
        # Extract the string value (without quotes)
        value = updated_node.evaluated_value
        if isinstance(value, str) and value.startswith(self.old_prefix):
            self.changes_made += 1
            new_value = self.new_prefix + value[len(self.old_prefix):]
            # Preserve the quote style
            quote = updated_node.value[0]
            return updated_node.with_changes(value=f'{quote}{new_value}{quote}')
        return updated_node
```

**Key points:**

- Use `evaluated_value` to get actual string content
- Preserve quote style (single vs double quotes)
- Handle f-strings separately (they use `FormattedString` node)

### Pattern 5: Work with Decorators

**Goal:** Add, remove, or modify decorators.

```python
from libcst import matchers as m

class AddDecoratorTransformer(cst.CSTTransformer):
    def __init__(self, decorator_name: str, target_function: str):
        super().__init__()
        self.decorator_name = decorator_name
        self.target_function = target_function
        self.changes_made = 0

    def leave_FunctionDef(self, original_node, updated_node):
        if not m.matches(updated_node, m.FunctionDef(name=m.Name(self.target_function))):
            return updated_node

        # Check if decorator already exists
        for decorator in updated_node.decorators:
            if m.matches(decorator.decorator, m.Name(self.decorator_name)):
                return updated_node  # Already has it

        # Add new decorator
        new_decorator = cst.Decorator(decorator=cst.Name(self.decorator_name))
        self.changes_made += 1

        return updated_node.with_changes(
            decorators=list(updated_node.decorators) + [new_decorator]
        )
```

**Key points:**

- Decorators is a sequence, create new list
- Check for duplicates before adding
- Preserve existing decorator order

### Pattern 6: Conditional Transformations with State

**Goal:** Transform nodes based on context from parent nodes.

```python
from libcst import matchers as m

class ConditionalTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.in_test_class = False
        self.changes_made = 0

    def visit_ClassDef(self, node):
        # Track if we're inside a test class
        if node.name.value.startswith("Test"):
            self.in_test_class = True
        return True

    def leave_ClassDef(self, original_node, updated_node):
        # Reset when leaving class
        if updated_node.name.value.startswith("Test"):
            self.in_test_class = False
        return updated_node

    def leave_FunctionDef(self, original_node, updated_node):
        # Only transform methods inside test classes
        if self.in_test_class and updated_node.name.value.startswith("test_"):
            self.changes_made += 1
            # Add decorator or modify function
            return updated_node  # ... with changes
        return updated_node
```

**Key points:**

- Use `visit_*` to track state
- Use `leave_*` to reset state and make transformations
- State tracking enables context-aware transformations

### Pattern 7: Using Matcher Decorators (Advanced)

**Goal:** Cleaner code using matcher decorators.

```python
from libcst import matchers as m

class MatcherDecoratorTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.changes_made = 0

    @m.call_if_inside(m.ClassDef(name=m.Name("MyClass")))
    @m.leave(m.FunctionDef(name=m.Name("old_method")))
    def rename_method(self, original_node, updated_node):
        self.changes_made += 1
        return updated_node.with_changes(name=cst.Name("new_method"))
```

**Key points:**

- `@m.leave()` specifies the pattern to match
- `@m.call_if_inside()` adds context requirements
- Cleaner than manual state tracking for simple cases
- Can be harder to debug than explicit logic

### Pattern 8: Complex Pattern Matching

**Goal:** Match complex nested structures.

```python
from libcst import matchers as m

class ComplexMatchTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.changes_made = 0

    def leave_Call(self, original_node, updated_node):
        # Match: old_func(x, y=z) where y is a keyword argument
        pattern = m.Call(
            func=m.Name("old_func"),
            args=[
                m.Arg(value=m.DoNotCare()),  # First positional arg (any value)
                m.Arg(keyword=m.Name("y"), value=m.DoNotCare())  # Keyword arg y
            ]
        )

        if m.matches(updated_node, pattern):
            self.changes_made += 1
            # Transform to new_func(x, y=z)
            return updated_node.with_changes(func=cst.Name("new_func"))
        return updated_node
```

**Key points:**

- Use `m.DoNotCare()` for "match anything" placeholders
- Use `m.OneOf()` for alternatives: `m.Name(m.OneOf("foo", "bar"))`
- Use `m.AllOf()` for multiple constraints
- Nest matchers to match deep structures

### Pattern 9: Insert Multiple Statements (FlattenSentinel)

**Goal:** Replace one statement with multiple statements (e.g., add logging before return).

```python
from libcst import matchers as m, FlattenSentinel

class AddLoggingTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.changes_made = 0

    def leave_Return(self, original_node, updated_node):
        # Add logging statement before every return
        log_stmt = cst.SimpleStatementLine([
            cst.Expr(cst.parse_expression("print('returning')"))
        ])
        self.changes_made += 1

        # FlattenSentinel inserts multiple statements in place of one
        return FlattenSentinel([log_stmt, updated_node])
```

**Key points:**

- `FlattenSentinel` replaces one node with multiple nodes
- Perfect for inserting debug code, logging, or wrapper statements
- Works with both simple and compound statements
- Each item in the list must be a complete statement node

**Common use cases:**

- Add logging before/after operations
- Insert guard clauses or validation
- Wrap existing code with try/except blocks

### Pattern 10: Remove Nodes Cleanly (RemoveFromParent)

**Goal:** Delete nodes from the tree (e.g., remove deprecated decorators or arguments).

```python
from libcst import matchers as m
from libcst import RemoveFromParent

class RemoveDecoratorTransformer(cst.CSTTransformer):
    def __init__(self, decorator_name: str):
        super().__init__()
        self.decorator_name = decorator_name
        self.changes_made = 0

    def leave_Decorator(self, original_node, updated_node):
        # Remove specific decorator
        if m.matches(updated_node.decorator, m.Name(self.decorator_name)):
            self.changes_made += 1
            return RemoveFromParent()
        return updated_node

# Also works for removing arguments, imports, etc.
class RemoveKeywordArgTransformer(cst.CSTTransformer):
    def leave_Arg(self, original_node, updated_node):
        # Remove keyword argument named "deprecated_param"
        if updated_node.keyword and updated_node.keyword.value == "deprecated_param":
            return RemoveFromParent()
        return updated_node
```

**Key points:**

- `RemoveFromParent()` is clearer than `RemovalSentinel.REMOVE`
- Works for any node type that can be removed
- LibCST handles trailing commas and formatting automatically
- Use matchers to identify what to remove

**Common use cases:**

- Remove deprecated decorators
- Delete unused arguments
- Clean up obsolete imports
- Remove debug statements

### Pattern 11: Template-Based Code Generation

**Goal:** Generate complex code with variable substitution using templates.

```python
from libcst.helpers import parse_template_statement, parse_template_expression, parse_template_module
from libcst import matchers as m

class ConvertToPropertyTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.changes_made = 0

    def leave_FunctionDef(self, original_node, updated_node):
        # Convert getter methods to @property
        if updated_node.name.value.startswith("get_"):
            prop_name = updated_node.name.value[4:]  # Remove "get_" prefix
            self.changes_made += 1

            module = cst.parse_module("")

            # Use template to generate property with decorator
            new_func = parse_template_statement(
                """
                @property
                def {name}(self):
                    {body}
                """,
                name=cst.Name(prop_name),
                body=updated_node.body,
                config=module.config_for_parsing
            )
            return new_func
        return updated_node

# Template expressions for complex code
class AddValidationTransformer(cst.CSTTransformer):
    def leave_FunctionDef(self, original_node, updated_node):
        module = cst.parse_module("")

        # Generate assert statement with template
        validation = parse_template_statement(
            "assert {param} is not None, 'Parameter cannot be None'",
            param=cst.Name("value"),
            config=module.config_for_parsing
        )

        # Insert at beginning of function body
        new_body = [validation] + list(updated_node.body.body)
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )
```

**Key points:**

- Use `{placeholder}` for variable substitution
- Much cleaner than manual node construction
- Works for statements, expressions, and entire modules
- Always use `config=module.config_for_parsing` for correct formatting
- Can substitute entire AST subtrees, not just simple values

**Template functions:**

- `parse_template_statement()` - For statements (if, for, assert, etc.)
- `parse_template_expression()` - For expressions (calls, operations, etc.)
- `parse_template_module()` - For entire modules

**When to use templates:**

- Complex code generation with variable parts
- Mixing literal structure with dynamic values
- When manual construction becomes unreadable

## 5 Critical Gotchas & Solutions

### Gotcha 1: Inserting New Lines Creates Semicolons

**Problem:** LibCST may insert semicolons when adding new simple statements.

```python
# ❌ WRONG: Creates "pass; new_statement" on one line with semicolon
def leave_Pass(self, original_node, updated_node):
    return [updated_node, cst.Expr(cst.Name("new_statement"))]
```

**Solution:** Use `FlattenSentinel` and wrap in `SimpleStatementLine`:

```python
# ✅ CORRECT: Creates proper new line
from libcst import FlattenSentinel

def leave_SimpleStatementLine(self, original_node, updated_node):
    if m.matches(updated_node.body[0], m.Pass()):
        return FlattenSentinel([
            updated_node,  # Keep the pass
            cst.SimpleStatementLine([cst.Expr(cst.Name("new_statement"))])
        ])
    return updated_node
```

### Gotcha 2: Immutable Nodes

**Problem:** LibCST nodes are immutable; modifying them directly fails.

```python
# ❌ WRONG: Nodes are immutable
def leave_FunctionDef(self, original_node, updated_node):
    updated_node.name = cst.Name("new_name")  # ← AttributeError!
    return updated_node
```

**Solution:** Use `.with_changes()`:

```python
# ✅ CORRECT: Create new node with changes
def leave_FunctionDef(self, original_node, updated_node):
    return updated_node.with_changes(name=cst.Name("new_name"))
```

### Gotcha 3: Lost Commas in Sequences

**Problem:** Adding items to sequences (args, params, list elements) without proper commas.

```python
# ❌ WRONG: Missing comma handling
new_args = list(original_node.args) + [cst.Arg(cst.Name("new_arg"))]
# ← Last item needs comma!
```

**Solution:** Use `MaybeSentinel.DEFAULT` for trailing commas:

```python
# ✅ CORRECT: Proper comma handling
from libcst import MaybeSentinel

new_arg = cst.Arg(
    value=cst.Name("new_arg"),
    comma=MaybeSentinel.DEFAULT  # LibCST figures out if comma needed
)
new_args = list(original_node.args) + [new_arg]
```

**Or parse from string:**

```python
# ✅ CORRECT: Parse from string handles commas automatically
module = cst.parse_module("")
new_call = cst.parse_expression(
    "func(x, y, new_arg)",
    config=module.config_for_parsing
)
```

### Gotcha 4: Whitespace Madness

**Problem:** Manually constructed nodes often have wrong spacing.

```python
# ❌ WRONG: Spacing is unpredictable
new_node = cst.BinaryOperation(
    left=cst.Name("x"),
    operator=cst.Add(),
    right=cst.Name("y")
)
# Might produce "x+y" or "x + y" or "x  +  y"
```

**Solution:** Parse from string when possible:

```python
# ✅ CORRECT: Parse from string = correct spacing
module = cst.parse_module("")
new_node = cst.parse_expression(
    "x + y",
    config=module.config_for_parsing
)
```

**Or use `.with_changes()` on existing nodes to preserve spacing:**

```python
# ✅ CORRECT: Preserve existing spacing
def leave_BinaryOperation(self, original_node, updated_node):
    return updated_node.with_changes(
        left=cst.Name("new_x")  # Spacing preserved from original
    )
```

### Gotcha 5: Module-Level Comments

**Problem:** Comments at module level can be tricky to preserve.

**Solution:** Access module-level comments via `header` and `footer`:

```python
def transform_file(file_path: Path) -> None:
    tree = cst.parse_module(source)

    # Preserve header comments (module docstring, file-level comments)
    # They're already part of the tree structure

    new_tree = tree.visit(transformer)

    # tree.header and tree.footer contain leading/trailing trivia
    # .visit() preserves them automatically
```

**Key insight:** LibCST preserves comments automatically in most cases. Only manually handle them if doing complex restructuring.

## 4 Debugging Techniques

### Technique 1: Print the Tree

**Always visualize before transforming:**

```python
import libcst as cst

code = '''
def foo(x: int) -> str:
    return str(x)
'''

tree = cst.parse_module(code)
print(tree)  # See the full structure

# Or pretty-print specific nodes
print(tree.body[0])  # Just the function
```

**This shows:**

- Exact node types
- Structure hierarchy
- Where small statements live (inside SimpleStatementLine)
- Whitespace nodes

### Technique 2: Use deep_equals to Check Changes

**Verify transformations are working:**

```python
import libcst as cst

original = cst.parse_module("def foo(): pass")
transformed = original.visit(MyTransformer())

if cst.deep_equals(original, transformed):
    print("No changes made!")
else:
    print("Transformation applied")
    print(transformed.code)
```

**Useful for:**

- Debugging why changes aren't being applied
- Verifying transformer logic
- Testing in isolation

### Technique 3: Unit Test Pattern

**Test transformers in isolation:**

```python
import libcst as cst

def test_rename_function():
    code = "def old_name(): pass"
    expected = "def new_name(): pass"

    tree = cst.parse_module(code)
    transformer = RenameFunctionTransformer("old_name", "new_name")
    new_tree = tree.visit(transformer)

    assert new_tree.code == expected
    assert transformer.changes_made == 1
```

**Benefits:**

- Fast feedback loop
- Isolate edge cases
- Document expected behavior

### Technique 4: Print Node Positions (PositionProvider)

**Use metadata to get line/column numbers for debugging:**

```python
import libcst as cst
from libcst.metadata import PositionProvider, MetadataWrapper

class DebugVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def visit_Name(self, node: cst.Name) -> None:
        # Get position metadata for the node
        pos = self.get_metadata(PositionProvider, node)
        print(f"Name '{node.value}' at line {pos.start.line}, column {pos.start.column}")

# Use MetadataWrapper to enable metadata
code = '''
def foo():
    x = 1
    y = 2
'''

wrapper = MetadataWrapper(cst.parse_module(code))
visitor = DebugVisitor()
wrapper.visit(visitor)

# Output:
# Name 'foo' at line 2, column 5
# Name 'x' at line 3, column 5
# Name 'y' at line 4, column 5
```

**Use cases:**

- Debug which nodes are being matched
- Print locations of transformations
- Generate detailed change reports
- Find nodes in specific line ranges

**Note:** Requires wrapping module with `MetadataWrapper` to compute positions.

## 4 Execution Strategies

### Strategy 1: Test on One File First

**Always validate on a single file before running across codebase:**

```bash
# Create test file
echo 'def old_name(): pass' > test_file.py

# Run transformer
python refactor_script.py test_file.py

# Verify output
cat test_file.py  # Should show: def new_name(): pass

# Revert for clean test
git checkout test_file.py
```

### Strategy 2: Progressive Rollout

**Apply transformations in stages:**

```bash
# Stage 1: One file
python refactor_script.py src/core.py --dry-run
python refactor_script.py src/core.py

# Stage 2: One directory
python refactor_script.py src/models/*.py --dry-run
python refactor_script.py src/models/*.py

# Stage 3: Full codebase
python refactor_script.py src/**/*.py --dry-run
python refactor_script.py src/**/*.py
```

### Strategy 3: Git-Tracked Files Only

**Only transform files tracked by git:**

```python
import subprocess

def get_git_tracked_files(directory: Path) -> list[Path]:
    """Get Python files tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True
    )
    return [Path(directory) / line for line in result.stdout.splitlines()]

# Use in main()
for file_path in get_git_tracked_files(Path("src")):
    transform_file(file_path, dry_run=False)
```

**Benefits:**

- Avoids transforming generated files
- Avoids build artifacts
- Easy to review changes with git diff

### Strategy 4: Dry Run First

**Always preview changes before applying:**

```python
def main():
    dry_run = "--dry-run" in sys.argv

    for file_path in get_python_files():
        if transform_file(file_path, dry_run=dry_run):
            if dry_run:
                print(f"[DRY RUN] Would modify: {file_path}")
            else:
                print(f"✓ Modified: {file_path}")
```

**Then:**

```bash
# Preview
python refactor_script.py src/**/*.py --dry-run

# Apply
python refactor_script.py src/**/*.py
```

## Rapid Patterns

**Quick one-liner patterns for common tasks:**

```python
# Find all function definitions named "foo"
from libcst import matchers as m
if m.matches(node, m.FunctionDef(name=m.Name("foo"))): ...

# Find all calls to "old_func"
if m.matches(node, m.Call(func=m.Name("old_func"))): ...

# Find all imports of "old_module"
if m.matches(node, m.ImportFrom(module=m.Name("old_module"))): ...

# Find all classes inheriting from "Base"
if m.matches(node, m.ClassDef(bases=[m.Arg(value=m.Name("Base"))])): ...

# Find all string literals starting with "test_"
if m.matches(node, m.SimpleString()) and node.evaluated_value.startswith("test_"): ...
```

## Recovery Commands

**Git safety net for when things go wrong:**

```bash
# See what changed
git diff

# Revert specific file
git checkout -- path/to/file.py

# Revert all changes
git checkout -- .

# Revert all Python files in directory
git checkout -- src/**/*.py

# Create safety branch before running
git checkout -b refactor-backup
# ... run transformations ...
# If bad: git checkout main && git branch -D refactor-backup
# If good: git checkout main && git merge refactor-backup
```

**Best practice:** Always commit before running transformations:

```bash
git add -A
git commit -m "Pre-refactor snapshot"
# ... run transformations ...
# If bad: git reset --hard HEAD
```

## When to Give Up

**LibCST isn't always the right tool. Use manual refactoring when:**

- ❌ Transformation only affects 2-3 files (faster to edit manually)
- ❌ Logic is extremely context-dependent (requires human judgment)
- ❌ You're spending >30 minutes debugging matcher logic (diminishing returns)
- ❌ Code has parsing errors (fix those first, or exclude from transformation)
- ❌ Formatting is critical and LibCST is mangling it (use IDE refactoring instead)

**Signs LibCST is the right tool:**

- ✅ Transformation is mechanical and repeatable
- ✅ Affects 10+ files
- ✅ Pattern is well-defined (rename, add arg, change import)
- ✅ You can express it clearly with matchers
- ✅ Dry run shows expected results

**Remember:** LibCST is for surgical precision, not exploratory surgery. If you can't clearly define the transformation, manual refactoring is often faster.

## Advanced: Scope-Aware Refactoring

For complex refactorings that need to understand variable scope, imports, and qualified names, LibCST provides metadata providers.

### Pattern A: Safe Variable Renaming with ScopeProvider

**Problem:** Renaming variables naively can break code when there are shadowed variables or multiple scopes.

```python
import libcst as cst
from libcst import matchers as m
from libcst.metadata import ScopeProvider, MetadataWrapper

class SafeRenameTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (ScopeProvider,)

    def __init__(self, old_name: str, new_name: str, target_scope_type: str = "global"):
        super().__init__()
        self.old_name = old_name
        self.new_name = new_name
        self.target_scope_type = target_scope_type
        self.changes_made = 0

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if updated_node.value != self.old_name:
            return updated_node

        # Get scope information for this name
        scope = self.get_metadata(ScopeProvider, original_node)

        # Check if this name is in the target scope
        if scope.__class__.__name__ == f"{self.target_scope_type.capitalize()}Scope":
            self.changes_made += 1
            return updated_node.with_changes(value=self.new_name)

        return updated_node

# Usage with MetadataWrapper
code = '''
x = 1  # Global scope

def foo():
    x = 2  # Function scope (shadowed)
    return x
'''

wrapper = MetadataWrapper(cst.parse_module(code))
transformer = SafeRenameTransformer("x", "global_x", target_scope_type="global")
new_tree = wrapper.visit(transformer)
print(new_tree.code)

# Output:
# global_x = 1  # Only global x renamed
#
# def foo():
#     x = 2  # Function scope NOT renamed
#     return x
```

**Use cases:**

- Rename global variables without affecting local variables
- Rename class attributes without affecting parameter names
- Understand which scope a variable belongs to

**ScopeProvider gives you:**

- `GlobalScope` - Module-level variables
- `FunctionScope` - Variables inside functions
- `ClassScope` - Class attributes
- `ComprehensionScope` - List/dict comprehension variables

### Pattern B: Import-Aware Transformations with QualifiedNameProvider

**Problem:** Converting `typing.List` to `list` requires understanding how List was imported.

```python
import libcst as cst
from libcst import matchers as m
from libcst.metadata import QualifiedNameProvider, MetadataWrapper

class ConvertTypingListTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    def __init__(self):
        super().__init__()
        self.changes_made = 0

    def leave_Subscript(self, original_node: cst.Subscript, updated_node: cst.Subscript) -> cst.Subscript:
        # Get qualified names for the subscripted value
        qualified_names = self.get_metadata(QualifiedNameProvider, original_node.value, set())

        # Check if this is typing.List
        for qname in qualified_names:
            if qname.name == "typing.List":
                self.changes_made += 1
                # Replace with built-in list
                return updated_node.with_changes(value=cst.Name("list"))

        return updated_node

# Handles all these import styles:
# import typing; typing.List[int]  → list[int]
# from typing import List; List[int]  → list[int]
# from typing import List as L; L[int]  → list[int]
```

**Use cases:**

- Convert type annotations (typing.List → list, typing.Dict → dict)
- Find usages of specific imported functions
- Handle various import aliases correctly

**QualifiedNameProvider resolves:**

- Direct imports: `import foo; foo.bar`
- From imports: `from foo import bar; bar`
- Aliased imports: `from foo import bar as baz; baz`

### Pattern C: deep_replace() for Complex Replacements

**Problem:** Need to replace a node deep in the tree without writing multiple visitor methods.

```python
import libcst as cst

class DeepReplaceExample(cst.CSTTransformer):
    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        # Replace specific argument deep in the call
        if isinstance(updated_node.func, cst.Name) and updated_node.func.value == "target_func":
            # deep_replace finds and replaces nodes recursively
            return updated_node.deep_replace(
                cst.Name("old_arg"),
                cst.Name("new_arg")
            )
        return updated_node
```

**Use cases:**

- Replace all occurrences of a node within a subtree
- Avoid writing multiple visitor methods for deep changes
- Quick fixes for nested structures

**Warning:** `deep_replace()` is less precise than visitor-based transformations. Use for simple replacements only.

### Pattern D: BatchableCSTVisitor for Performance

**Problem:** Running multiple transformations requires multiple tree traversals.

```python
import libcst as cst
from libcst.metadata import MetadataWrapper
from libcst import BatchableCSTVisitor

class CollectNames(BatchableCSTVisitor):
    def __init__(self):
        super().__init__()
        self.names = []

    def visit_Name(self, node: cst.Name) -> None:
        self.names.append(node.value)

class CollectFunctions(BatchableCSTVisitor):
    def __init__(self):
        super().__init__()
        self.functions = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.functions.append(node.name.value)

# Run both visitors in a single traversal
code = '''
def foo():
    x = 1
def bar():
    y = 2
'''

module = cst.parse_module(code)
visitor1 = CollectNames()
visitor2 = CollectFunctions()

# Single traversal for both visitors
module.visit_batched([visitor1, visitor2])

print(visitor1.names)  # ['foo', 'x', 'bar', 'y']
print(visitor2.functions)  # ['foo', 'bar']
```

**Use cases:**

- Collect multiple types of information in one pass
- Performance optimization for large codebases
- When running multiple analysis passes

**Note:** Only for read-only analysis (visitors), not transformations.

## Common Helper Utilities

LibCST provides helper functions that simplify common tasks:

### ensure_type() - Type-Safe Assertions

```python
import libcst as cst
from libcst import matchers as m

# ❌ WRONG: isinstance + assert
if m.matches(node, m.Name()):
    assert isinstance(node, cst.Name)
    value = node.value

# ✅ CORRECT: ensure_type
if m.matches(node, m.Name()):
    value = cst.ensure_type(node, cst.Name).value
    # Type checker knows node is cst.Name
```

**Benefits:**

- Type-checker friendly
- More concise than isinstance + assert
- Raises clear error if type mismatch

### AddImportsVisitor / RemoveImportsVisitor - Safe Import Management

For ephemeral scripts, manual import manipulation is usually fine. But for production-quality codemods, use the official import helpers:

```python
from libcst.codemod.visitors import AddImportsVisitor, RemoveImportsVisitor
from libcst.codemod import CodemodContext

class MyTransformer(cst.CSTTransformer):
    def __init__(self, context: CodemodContext):
        super().__init__()
        self.context = context

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        # Add import at module level
        AddImportsVisitor.add_needed_import(self.context, "typing", "List")

        # Remove unused import
        RemoveImportsVisitor.remove_unused_import(self.context, "typing", "Dict")

        return updated_node
```

**Handles:**

- Import deduplication
- Proper import sorting and grouping
- Updating existing from imports
- Preserving import style

**Note:** Requires CodemodContext, which is heavier than simple transformers. For ephemeral scripts, manual import handling is often simpler.

### get_full_name_for_node() - Extract Dotted Names

```python
from libcst.helpers import get_full_name_for_node
import libcst as cst

code = "foo.bar.baz"
node = cst.parse_expression(code)

# node is Attribute(Attribute(Name("foo"), Name("bar")), Name("baz"))
name = get_full_name_for_node(node)  # "foo.bar.baz"
```

**Use cases:**

- Extract full qualified names from Attribute chains
- Match against dotted names in patterns
- Logging and debugging

**Returns None if node is not a Name or Attribute.**
