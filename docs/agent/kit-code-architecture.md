# Kit Code Architecture

## Two-Layer Architecture

Kit code lives in exactly TWO places:

### Layer 1: Canonical Implementation (erk-shared)

**Location**: `packages/erk-shared/src/erk_shared/integrations/[kit_name]/`

**What goes here**: All actual implementation code

```
packages/erk-shared/src/erk_shared/integrations/gt/
├── __init__.py                      # Public exports
├── abc.py                           # ABC interfaces
├── real.py                          # Real implementations
├── fake.py                          # Test fakes
├── types.py                         # Type definitions
├── prompts.py                       # Utilities
└── kit_cli_commands/
    └── gt/
        ├── submit_branch.py         # ACTUAL implementation (1000+ lines)
        ├── land_branch.py
        └── pr_update.py
```

**Rules**:

- ✅ All actual code goes here
- ❌ NO imports from `erk` package
- ❌ NO imports from `dot-agent-kit` package

### Layer 2: Kit Definition (dot-agent-kit)

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit_name]/`

**What goes here**: Kit metadata + thin shims (10-20 lines each)

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/
├── kit.yaml                         # Kit metadata
├── kit_cli_commands/
│   └── gt/
│       ├── submit_branch.py         # Shim (imports from erk-shared)
│       ├── land_branch.py           # Shim
│       └── pr_update.py             # Shim
├── agents/                          # Agent definitions
├── commands/                        # Command definitions
└── skills/                          # Skill definitions
```

**Rules**:

- ✅ Thin shims that re-export from erk-shared
- ✅ Kit metadata (kit.yaml, agents/, commands/, skills/)
- ❌ NO actual implementation code

**Example Shim**:

```python
# packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py
"""Re-export from erk-shared."""

from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    execute_finalize,
    execute_pre_analysis,
    execute_preflight,
    get_diff_context,
    pr_submit,
)

__all__ = ["execute_pre_analysis", "execute_preflight", "execute_finalize", "get_diff_context", "pr_submit"]
```

## Architecture Diagram

```
┌───────────────────────────────────────┐
│ dot-agent-kit/data/kits/gt/           │
│   ├── kit.yaml                        │
│   └── kit_cli_commands/gt/            │
│       └── submit_branch.py (shim)     │
│              ↓ imports                │
└───────────────────────────────────────┘
             ↓
┌───────────────────────────────────────┐
│ erk-shared/integrations/gt/           │
│   ├── abc.py                          │
│   ├── real.py                         │
│   ├── fake.py                         │
│   └── kit_cli_commands/gt/            │
│       └── submit_branch.py (1000+loc) │
└───────────────────────────────────────┘
```

## Testing

Always import from erk-shared:

```python
# ✅ CORRECT
from erk_shared.integrations.gt import RealGtKit
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import pr_submit

# ❌ WRONG - don't import from kit location
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.submit_branch import pr_submit
```

## Validation Test

```python
def test_gt_kit_architecture() -> None:
    """Verify correct two-layer architecture."""

    # Layer 1: Implementation exists in erk-shared
    impl = Path("packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py")
    assert impl.exists()

    # Layer 2: Shim exists in dot-agent-kit
    shim = Path("packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py")
    assert shim.exists()
    assert "from erk_shared.integrations.gt" in shim.read_text()
```

## Quick Reference

**Q: Where do I put new kit command code?**
A: `packages/erk-shared/src/erk_shared/integrations/[kit_name]/kit_cli_commands/`

**Q: Where do I define the kit structure?**
A: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit_name]/kit.yaml`

**Q: What goes in kit_cli_commands in dot-agent-kit?**
A: Thin shims (10-20 lines) that import from erk-shared

**Q: How do I know if code belongs in erk-shared?**
A: If it has more than 20 lines of logic, it goes in erk-shared
