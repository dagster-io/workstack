# Enable mark-step to Accept Multiple Steps

## Problem

`dot-agent run erk mark-step` is called in parallel by Claude, causing lost updates due to read-modify-write race conditions on `.impl/progress.md`. When multiple `mark-step` commands run concurrently, they all read the same initial state, modify independently, and the last writer wins—losing all other updates.

## Solution

Two-pronged approach:
1. **Enable batch marking**: Modify `mark-step` to accept multiple step numbers in a single invocation
2. **Add prompting**: Document that this command should NOT be parallelized

## Implementation Steps

### 1. Update mark-step CLI to accept multiple steps

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/mark_step.py`

- Change Click argument from single to variadic:
  ```python
  # Before
  @click.argument("step_num", type=int)

  # After
  @click.argument("step_nums", type=int, nargs=-1)
  ```

- Update function signature: `step_num: int` → `step_nums: tuple[int, ...]`

- Add validation for empty tuple (require at least one step)

- Add validation pass before any modifications (fail fast on invalid step):
  ```python
  # Validate all steps first
  for step_num in step_nums:
      if step_num < 1 or step_num > total_steps:
          _error(f"Step number {step_num} out of range (1-{total_steps})")

  # Then update all (single read-modify-write cycle)
  for step_num in step_nums:
      _update_step_status(metadata, step_num, completed)
  ```

- Update output format:
  - Human: List each marked step, then final progress
  - JSON: Change `step_num` to `step_nums` array

- Update module docstring with new usage examples

### 2. Add prompting to prevent parallel execution

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`

Add warning near mark-step usage (around line 215):

```markdown
6. **Mark phase as completed** when done:
   ```bash
   dot-agent run erk mark-step <step_number>
   ```

   **IMPORTANT - Sequential Execution Required:**
   - **NEVER** run multiple `mark-step` commands in parallel
   - This command modifies `.impl/progress.md` and parallel execution causes lost updates
   - If marking multiple steps, use a single command: `dot-agent run erk mark-step 1 2 3`
```

### 3. Update kit.yaml description

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`

Update the mark-step description to indicate multi-step support and sequential-only constraint.

### 4. Update tests

**File**: `packages/dot-agent-kit/tests/integration/kits/erk/test_mark_step_integration.py`

Add tests for:
- Multiple steps in single command
- JSON output with multiple steps (`step_nums` array)
- Error handling when one step is invalid (should fail entire batch, no partial writes)
- Empty args error

## Critical Files

- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/mark_step.py` - Core logic
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md` - Agent prompting
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml` - Command description
- `packages/dot-agent-kit/tests/integration/kits/erk/test_mark_step_integration.py` - Tests

## Backwards Compatibility

- Single-step usage unchanged: `mark-step 5` still works (tuple of one)
- JSON output changes from `step_num` (int) to `step_nums` (array) - breaking change but internal tooling only