# /gt:simple-update-pr

Simplified Graphite update-pr workflow for testing and performance comparison.

## Purpose

Provides a streamlined alternative to the standard `/gt:update-pr` command with:
- Fail-fast execution with natural error messages
- No error categorization or state tracking
- Simplified agent with minimal documentation
- Same core operations, drastically reduced complexity

## Usage

```bash
/gt:simple-update-pr
```

## Comparison with Standard Version

| Aspect | Simple Version | Standard Version |
|--------|---------------|------------------|
| Python code | ~70 lines | 173 lines |
| Agent docs | ~80 lines | 175 lines |
| Error types | None (natural) | 4 categorized |
| State tracking | None | `had_changes` field |
| Output format | Simple dict | Dataclasses |
| Token usage | ~60% less | Baseline |
| Execution time | Same | Same |

## When to Use Each Version

**Use simple version when:**
- Working on standard update workflows
- Want faster Claude interaction
- Prefer natural error messages
- Testing performance improvements

**Use standard version when:**
- Need detailed error categorization
- Want specific guidance for each error type
- Require state tracking information
- Debugging complex issues

## Example Output

**Success:**
```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123"
}
```

**Error:**
```json
{
  "success": false,
  "error": "No PR associated with current branch"
}
```

## Notes

- This is an experimental command for A/B testing
- Uses the same underlying operations as standard version
- If successful in testing, may become the default implementation
- Follows the simplification pattern from `/gt:simple-submit`