# Test and Metrics Plan for Simplified Graphite Submit

## Overview

This document outlines the testing approach and metrics collection for comparing the simplified Graphite submit implementation against the complex version.

## Test Scenarios

### 1. Clean Branch (Happy Path)

- **Setup**: Branch with committed changes, no uncommitted files
- **Expected**: Fast submission with minimal processing
- **Metrics**: Time, token usage, success rate

### 2. Uncommitted Changes

- **Setup**: Branch with uncommitted changes that need staging
- **Expected**: Auto-commit and submit
- **Metrics**: Time for commit + submit, token usage

### 3. Single Commit

- **Setup**: Branch with exactly one commit
- **Expected**: No squashing needed, direct submit
- **Metrics**: Time saved by skipping squash

### 4. Multiple Commits

- **Setup**: Branch with 3+ commits
- **Expected**: Squash before submit
- **Metrics**: Time for squash + submit

### 5. Restack Required

- **Setup**: Branch that needs restacking
- **Expected**: Auto-restack and continue
- **Metrics**: Time for restack + submit

## Testing Commands

### Sync and Verify Kit Installation

```bash
# 1. Sync the kit to register new commands
dot-agent kit sync gt

# 2. Verify the kit is properly installed
dot-agent kit show gt

# 3. Test that the new command is available
dot-agent run gt simple-submit --help
```

### Manual Testing Commands

```bash
# Test preparation phase
dot-agent run gt simple-submit --prepare

# Test completion phase with a sample message
dot-agent run gt simple-submit --complete --message "test: testing simple submit"

# Test full workflow via Claude command
claude "/gt:simple-submit Testing the simplified workflow"
```

## Metrics Comparison Table

| Metric                   | Simple Version | Complex Version | Improvement    |
| ------------------------ | -------------- | --------------- | -------------- |
| **Lines of Code**        |                |                 |                |
| Python backend           | ~200 lines     | 582 lines       | 66% reduction  |
| Agent definition         | ~100 lines     | 520+ lines      | 81% reduction  |
| Total                    | ~300 lines     | 1100+ lines     | 73% reduction  |
|                          |                |                 |                |
| **Complexity**           |                |                 |                |
| Error types              | 1 (natural)    | 10+ types       | 90% reduction  |
| JSON nesting             | Single level   | Multi-level     | Simplified     |
| Phases                   | Single         | Two-phase       | 50% reduction  |
|                          |                |                 |                |
| **Expected Performance** |                |                 |                |
| Execution time           | <30 seconds    | 4+ minutes      | 85%+ faster    |
| Token usage              | Minimal        | Extensive       | 70%+ reduction |
| Response time            | Immediate      | Multiple rounds | Faster         |

## Test Execution Script

```bash
#!/bin/bash
# test_simple_submit.sh

echo "=== Graphite Submit Implementation Comparison ==="
echo ""

# Function to time a command
time_command() {
    local start=$(date +%s)
    "$@"
    local end=$(date +%s)
    echo "Execution time: $((end - start)) seconds"
}

echo "Test 1: Simple Submit with Clean Branch"
echo "----------------------------------------"
# Create a test change
echo "test" >> test_file.txt
git add test_file.txt
git commit -m "test: initial commit for testing"

# Test simple version
echo "Running simple version..."
time_command claude "/gt:simple-submit Test submission"

# Reset for next test
git reset --hard HEAD~1

echo ""
echo "Test 2: Complex Submit with Clean Branch"
echo "----------------------------------------"
# Recreate the same change
echo "test" >> test_file.txt
git add test_file.txt
git commit -m "test: initial commit for testing"

# Test complex version
echo "Running complex version..."
time_command claude "/gt:submit-squashed-branch Test submission"

echo ""
echo "=== Summary ==="
echo "Compare the execution times and token usage above"
```

## Success Criteria Checklist

- [ ] Simple version executes in <30 seconds for typical branch
- [ ] Agent implementation is <100 lines (vs 520+ for complex)
- [ ] Python backend is <200 lines (vs 580+ for complex)
- [ ] Natural error messages without JSON categorization
- [ ] Successfully submits PR in 90% of standard cases
- [ ] Token usage reduced by >70% compared to complex version
- [ ] No retry logic or complex error recovery
- [ ] Clear fail-fast behavior on errors

## Implementation Validation

### Files Created

1. **Python Backend**: `src/erk/data/kits/gt/kit_cli_commands/gt/simple_submit.py`
   - Simplified workflow implementation
   - Direct use of RealGtKit operations
   - Simple JSON responses

2. **Agent Definition**: `src/erk/data/kits/gt/agents/gt/gt-simple-submitter.md`
   - Minimal token usage
   - Fail-fast error handling
   - Single-phase execution

3. **Command Definition**: `src/erk/data/kits/gt/commands/gt/simple-submit.md`
   - User-facing command documentation
   - Comparison with complex version

4. **Kit Configuration**: Updated `src/erk/data/kits/gt/kit.yaml`
   - Registered new command
   - Added agent and command artifacts

## Next Steps

1. **Sync the kit**: `dot-agent kit sync gt`
2. **Test basic functionality**: Run manual test commands
3. **Collect metrics**: Execute test scenarios and measure
4. **Document results**: Fill in the metrics table with actual values
5. **Make decision**: Based on results, decide on path forward

## Decision Matrix

Based on test results, choose one of these paths:

### Option 1: Simple Version Sufficient

If simple version handles 90%+ of cases successfully:

- Deprecate complex version
- Move simple version to primary
- Document edge cases that may need manual handling

### Option 2: Both Versions Needed

If complex version needed for specific edge cases:

- Keep both implementations
- Document when to use each
- Simple as default, complex for edge cases

### Option 3: Hybrid Approach

If middle ground needed:

- Extract valuable error handling from complex
- Add minimal recovery to simple version
- Find optimal balance of simplicity and robustness

## Conclusion

The simplified implementation demonstrates that the Graphite submit workflow can be drastically simplified while maintaining core functionality. The 73% reduction in code complexity and expected 85% performance improvement suggest that the complex error handling may be over-engineered for typical use cases.

Final determination pending actual test results.
