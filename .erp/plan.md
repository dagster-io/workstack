## Fix erk kit command import errors

### Problem
Three erk kit commands are failing to import with "No module named 'erk'" warnings:
1. `create-plan-from-context`
2. `create-enriched-plan-from-context`
3. `create-erp-from-issue`

### Root Cause
The commands have incorrect import statements using `erk.data.kits.erk` instead of `dot_agent_kit.data.kits.erk`.

### Implementation Steps

**1. Fix create_plan_from_context.py (line 21)**
```python
# Change from:
from erk.data.kits.erk.plan_utils import extract_title_from_plan
# To:
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan
```

**2. Fix create_enriched_plan_from_context.py (line 18)**
```python
# Change from:
from erk.data.kits.erk.plan_utils import extract_title_from_plan
# To:
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan
```

**3. Fix create_erp_from_issue.py (line 30)**
```python
# Change from:
from erk.core.context import create_context
# To:
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan
# AND investigate if this command actually needs erk.core.context access
```

**4. Verify fixes**
- Run `dot-agent run erk --help` to confirm no import warnings
- Test each command if possible

### Files to Edit
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_plan_from_context.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_enriched_plan_from_context.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_erp_from_issue.py`

## Context & Understanding

### Architectural Insights

All kit CLI commands run within the `dot_agent_kit` package namespace. The package structure is:
- Kit commands are located at: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/`
- Utility modules are at: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/`
- At runtime, imports must use `dot_agent_kit.*` paths, not `erk.*` paths

The `erk` package is a separate application package. Kit commands cannot import from it directly because:
1. Kit commands execute in the dot-agent-kit environment
2. The erk package may not be installed or available in that environment
3. Kit command utilities (like plan_utils.py) are co-located within dot_agent_kit

### Known Pitfalls

- **Wrong namespace**: Using `erk.data.kits.erk` assumes the directory structure matches the package name, but the actual package is `dot_agent_kit`
- **Source vs runtime confusion**: The files exist under `data/kits/erk/` directory, but that doesn't make them part of an `erk` package
- **Cross-package imports**: Kit commands should not depend on the main `erk` application package (create_erp_from_issue.py may need refactoring)

### Raw Discoveries Log

- All three command files use Click CLI framework with EAFP error handling
- `create_plan_from_context.py` reads from stdin, processes markdown, outputs JSON
- `create_enriched_plan_from_context.py` reads from file (--plan-file), validates, outputs JSON  
- `create_erp_from_issue.py` is structurally different - fetches GitHub issue, creates context, invokes plan store
- Verified `plan_utils.py` exists at `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/plan_utils.py` with `extract_title_from_plan` function
- Other working commands in same directory use `from dot_agent_kit.data.kits.erk.*` imports successfully

### Implementation Risks

- The three failing commands may have been copied from older code with different package structure
- `create_erp_from_issue.py` has a deeper issue - it imports `erk.core.context.create_context` which is from the main erk application
  - This suggests the command was intended to bridge between kit system and main erk app
  - May need architectural decision: should this command have erk as a dependency, or should it be refactored to not need erk.core.context?
- After fixing imports, need to test that plan_store functionality still works correctly
- The corrected import for create_erp_from_issue.py in the plan might be incorrect - needs investigation

### Complex Reasoning

The import errors reveal a package architecture boundary:
- **dot-agent-kit** contains kit infrastructure and bundled kits (including the erk kit)
- **erk** is the main application that uses worktrees and planning workflows
- Kit commands should be self-contained within dot-agent-kit
- If a kit command needs erk application functionality, it creates a dependency issue

The fix for the first two commands is straightforward (wrong package name). The third command (`create_erp_from_issue.py`) needs investigation:
- Does it genuinely need `erk.core.context`? 
- If yes: Should erk be a kit command dependency?
- If no: What alternative approach should it use?

### Planning Artifacts

- Examined three failing command files
- Examined plan_utils.py to confirm import target exists
- Examined other working commands to confirm correct import pattern
- Identified line numbers for all import statements
