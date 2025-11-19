# Import Organization - Module-Level and Absolute

## Core Rules

1. **Default: ALWAYS place imports at module level**
2. **Use absolute imports only** (no relative imports)
3. **Inline imports only for specific exceptions** (see below)

## Correct Import Patterns

```python
# ✅ CORRECT: Module-level imports
import json
import click
from pathlib import Path
from erk.config import load_config

def my_function() -> None:
    data = json.loads(content)
    click.echo("Processing")
    config = load_config()

# ❌ WRONG: Inline imports without justification
def my_function() -> None:
    import json  # NEVER do this
    import click  # NEVER do this
    data = json.loads(content)
```

## Legitimate Inline Import Patterns

### 1. Circular Import Prevention

```python
# commands/sync.py
def register_commands(cli_group):
    """Register commands with CLI group (avoids circular import)."""
    from myapp.cli import sync_command  # Breaks circular dependency
    cli_group.add_command(sync_command)
```

**When to use:**

- CLI command registration
- Plugin systems with bidirectional dependencies
- Lazy loading to break import cycles

### 2. Conditional Feature Imports

```python
def process_data(data: dict, dry_run: bool = False) -> None:
    if dry_run:
        # Inline import: Only needed for dry-run mode
        from myapp.dry_run import NoopProcessor
        processor = NoopProcessor()
    else:
        processor = RealProcessor()
    processor.execute(data)
```

**When to use:**

- Debug/verbose mode utilities
- Dry-run mode wrappers
- Optional feature modules
- Platform-specific implementations

### 3. TYPE_CHECKING Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myapp.models import User  # Only for type hints

def process_user(user: "User") -> None:
    ...
```

**When to use:**

- Type annotations causing circular imports
- Expensive modules only for type checking
- Forward references

### 4. Performance Optimization (Use Sparingly)

```python
def analyze_data(data: dict) -> Report:
    # Inline import: tensorflow takes 30+ seconds to load
    import tensorflow as tf
    model = tf.load_model("model.h5")
    return model.predict(data)
```

**When to use:**

- ML libraries with 10+ second import times
- Large data processing modules
- Expensive module initialization

### 5. Test-Only Utilities

```python
def test_api_endpoint():
    # Test infrastructure import
    from myapp.testing import create_mock_client
    client = create_mock_client()
    assert client.get("/health") == 200
```

## Import Organization Best Practices

```python
# Standard library imports
import json
import os
from pathlib import Path

# Third-party imports
import click
import numpy as np
from pydantic import BaseModel

# Local application imports
from erk.config import load_config
from erk.utils import format_output
```

## `__all__` Exports in `__init__.py`

```python
# myapp/__init__.py
"""Public API for myapp package."""

from myapp.core import Process
from myapp.utils import format_data

# Define public API explicitly
__all__ = ["Process", "format_data"]
```

## Key Takeaways

1. **Module-level default**: Place imports at top of file
2. **Absolute imports**: Use full paths from project root
3. **Document inline imports**: Explain why import is inline
4. **Organize by source**: stdlib → third-party → local
5. **Public API**: Use `__all__` to define package exports
