<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# Plan: Convert plan-extractor from JSON to Markdown Output

## Enrichment Details

### Process Summary
- **Mode**: enriched
- **Guidance applied**: no
- **Questions asked**: 3
- **Context categories extracted**: 5 of 8

### Clarifications Made
1. **Error Format**: Keep textual-only markdown format for simplicity - errors detected via grep for `^## Error:` prefix
2. **Enrichment Details Section**: Always included in all successful outputs for consistency and transparency
3. **Validation Approach**: Use basic markdown structure validation (checking required headings) instead of kit CLI to avoid adding complexity and failure modes

### Context Categories Populated
- ✅ Architectural Insights
- ✅ Complex Reasoning
- ✅ Known Pitfalls
- ✅ Raw Discoveries Log
- ✅ Implementation Risks
- ❌ API/Tool Quirks (none found)
- ❌ Domain Logic & Business Rules (none found)
- ❌ Planning Artifacts (none found)

---

## Overview

Change the plan-extractor agent to return markdown instead of JSON. The current JSON wrapper adds parsing complexity without providing value since the parent commands only need:
- Success/failure status
- Plan title
- Plan content (already markdown)

## Rationale

**Current state problems:**
1. JSON wraps markdown that gets immediately unwrapped via `jq`
2. `enrichment` metadata fields aren't programmatically used by parent commands
3. Adds bash `jq` parsing complexity and failure modes
4. LLMs parse markdown better than JSON

**After change:**
1. Agent returns markdown directly
2. Parent extracts title from first `#` heading
3. Error detection via `## Error:` prefix (simple text match)
4. Cleaner, more readable output

## Files to Modify

### 1. Agent: `.claude/agents/erk/plan-extractor.md`

**Changes:**
- Replace JSON output format section with markdown format
- Update output examples throughout
- Update validation section (return markdown errors, not JSON)
- Update self-verification checklist

**New output format (success):**

```markdown
# Plan: [title extracted from plan]

## Enrichment Details

### Process Summary
- **Mode**: enriched
- **Guidance applied**: yes/no
- **Guidance text**: "[original guidance if provided]"
- **Questions asked**: N
- **Context categories extracted**: N of 8

### Clarifications Made
[If questions were asked]
1. **[Question topic]**: [User's answer and how it was incorporated]
2. **[Question topic]**: [User's answer and how it was incorporated]

### Context Categories Populated
[List which of the 8 categories had content extracted]
- ✅ API/Tool Quirks
- ✅ Architectural Insights
- ✅ Domain Logic & Business Rules
- ❌ Complex Reasoning (none found)
- ✅ Known Pitfalls
- ✅ Raw Discoveries Log
- ✅ Planning Artifacts
- ❌ Implementation Risks (none found)

---

## Implementation Plan

[Full plan content here...]

## Context & Understanding

### API/Tool Quirks
[Detailed content extracted during planning]

### Architectural Insights
[Detailed content extracted during planning]

### Domain Logic & Business Rules
[Detailed content extracted during planning]

### Known Pitfalls
[Detailed content extracted during planning]

### Raw Discoveries Log
[Everything discovered during planning]

### Planning Artifacts
[Code examined, commands run, configurations discovered]
```

**New output format (error):**

```markdown
## Error: [error_type]

[Human-readable error message]

### Details
[Additional context if available]
```

### 2. Command: `packages/dot-agent-kit/.../commands/erk/save-plan.md`

**Changes in Step 3 (Parse Agent Response):**

Replace jq parsing:
```bash
# OLD
plan_title=$(echo "$result" | jq -r '.plan_title')
plan_content=$(echo "$result" | jq -r '.plan_content')
```

With markdown parsing:
```bash
# NEW - Check for error
if echo "$result" | grep -q "^## Error:"; then
    # Extract error message
    error_msg=$(echo "$result" | sed -n 's/^## Error: //p')
    echo "❌ Error: $error_msg"
    exit 1
fi

# Extract title from first heading
plan_title=$(echo "$result" | grep -m1 "^# Plan:" | sed 's/^# Plan: //')

# Use full content for issue (or extract after ---)
plan_content="$result"
```

**Remove/simplify:**
- JSON validation logic
- jq dependency for this step
- Enrichment summary display (now embedded in markdown)

### 3. Command: `packages/dot-agent-kit/.../commands/erk/save-raw-plan.md`

**Same changes as save-plan.md** for Step 4 (Parse Agent Response):
- Replace jq parsing with grep/sed
- Simplify error detection
- Remove JSON validation

## Implementation Steps

1. **Update plan-extractor agent** (`plan-extractor.md`)
   - Change output format section from JSON to markdown
   - Update all examples showing expected output
   - Update error format section
   - Update validation instructions
   - Update self-verification checklist

2. **Update save-plan command** (`save-plan.md`)
   - Replace Step 3 JSON parsing with markdown parsing
   - Simplify error handling
   - Remove optional enrichment summary section (now in agent output)
   - Update architecture diagram in documentation

3. **Update save-raw-plan command** (`save-raw-plan.md`)
   - Replace Step 4 JSON parsing with markdown parsing
   - Simplify error handling
   - Update architecture diagram

## Error Format Standardization

Keep structured error detection with markdown:

| Error Type | Markdown Marker |
|------------|-----------------|
| No plan found | `## Error: no_plan_found` |
| Session not found | `## Error: session_not_found` |
| Guidance without plan | `## Error: guidance_without_plan` |
| Validation failed | `## Error: validation_failed` |

Parent commands can detect errors with: `grep -q "^## Error:"`

## Backward Compatibility

None required - this is internal agent communication, not a public API. Both the agent and commands are updated together.

## Testing

Manual testing:
1. Run `/erk:save-plan` with a plan in conversation
2. Run `/erk:save-raw-plan` with ExitPlanMode in session
3. Test error cases (no plan, invalid session)
4. Verify GitHub issue creation still works

## Context & Understanding

### Architectural Insights

**JSON wrapper complexity trade-off**: The current JSON design was originally intended to provide structured metadata (guidance_applied, questions_asked, context_categories) that parent commands could use for programmatic processing. However, in practice, parent commands only extract plan_title and plan_content via jq, leaving the enrichment metadata unused. This represents a design decision to prioritize "machine-readable metadata" over "simplicity" - a choice that now appears suboptimal given actual usage patterns.

**Markdown-first approach justification**: By returning markdown directly with embedded enrichment details, we align with how LLMs naturally produce output and how humans naturally read it. The enrichment details become self-documenting in the output, eliminating the need for separate JSON metadata extraction. This is a pattern shift from "structured data + human documentation" to "structured documentation as data".

**Agent output format as contract**: The change demonstrates that agent output format is an implementation detail of the agent-command contract, not a public API. Since both the agent and its consuming commands are updated together in this module, format changes have zero backward compatibility cost. This differs from user-facing command output which must maintain stability.

**Markdown over grep/sed for parsing**: The decision to use grep/sed instead of jq for markdown parsing trades off "structured parsing" for "simplicity and robustness". Regular expressions are simpler than JSON parsing, have fewer failure modes (no jq install dependency), and are more readable to shell script maintainers. The plan content itself remains well-structured markdown.

### Complex Reasoning

**Why textual-only errors (not structured metadata)**: The user selected textual-only error format over structured error codes/exit codes. This simplifies parent command error detection - a single `grep -q "^## Error:"` check replaces JSON parsing. The tradeoff: structured errors would allow more sophisticated programmatic error handling in parent commands, but current usage doesn't require this level of sophistication. Textual errors are simpler and sufficient.

**Why always include enrichment details**: The user selected to always include the enrichment details section in all successful outputs (not conditional on enrichment happening). This provides consistency and transparency - users always see what happened during enrichment, even if no guidance was applied or questions were asked. The alternative (conditional inclusion) would produce cleaner output in minimal-enrichment cases but creates inconsistent output shapes that consuming code must handle.

**Validation approach trade-off**: The user selected basic markdown structure validation over kit CLI validation. This choice eliminates a failure mode (kit CLI command failing) and avoids adding a runtime dependency check. However, it reduces validation thoroughness - basic structure checking won't catch semantic errors. This is acceptable because validation is informational (plan still returned even if validation fails) and the agent that generated the plan is already tested.

### Known Pitfalls

**Partial markdown extraction via sed/grep is fragile**: Using `grep -m1 "^# Plan:"` to extract titles assumes titles are always in a `# Plan: [title]` format. If a plan has multiple top-level headings or the format changes, extraction breaks silently. The safest approach: document this format requirement clearly and test extraction patterns thoroughly.

**Error prefix detection assumes consistent format**: Checking `grep -q "^## Error:"` for error detection requires all error outputs to start with this exact prefix. If any error-generating code path uses a different format (e.g., `## ERROR:` or `# Error:`), the detection fails. Solution: document the error format standard and enforce it through examples and validation.

**Whitespace handling in sed extraction**: The sed pattern `sed 's/^# Plan: //'` is vulnerable to variations in spacing (e.g., `# Plan:  ` with two spaces). A more robust pattern would be `sed 's/^# Plan: *\(.*\)/\1/'` to handle variable spacing. This matters if plan titles are auto-generated and might have formatting variations.

### Raw Discoveries Log

- Agent output currently returns JSON which gets parsed by parent commands using jq
- Parent commands (save-plan, save-raw-plan) only use `plan_title` and `plan_content` fields from agent JSON
- The `enrichment` metadata object (guidance_applied, questions_asked, clarifications, context_extracted, context_categories) is populated by the agent but never consumed by parent commands
- Plan content is already markdown-formatted when returned by agent
- Error detection in parent commands checks if JSON `.success` field is false
- Kit CLI validation command exists: `dot-agent run erk validate-plan-content`
- Current save-plan.md command has an optional Step 7 for displaying enrichment summary, but this summary duplicates information already in the plan_content
- Error scenarios in save-plan.md use plain text error messages, not JSON error responses
- The plan-extractor agent documentation describes step-by-step context extraction across 8 categories
- Both save-plan.md and save-raw-plan.md orchestrate the plan-extractor agent via Task tool
- Plan extraction workflow has a fallback: try session logs first (via kit CLI), then fall back to conversation search if that fails

### Implementation Risks

**Risk: Breaking change in agent contract**: If any other code consumes the agent's JSON output format directly (not just save-plan/save-raw-plan commands), this change will break it. Mitigation: Search codebase for all usages of plan-extractor agent before making change. Verify only save-plan.md and save-raw-plan.md consume this output.

**Risk: Markdown title extraction fragility**: Extracting plan title from first `# Plan:` heading using grep could fail if: (1) multiple `# Plan:` headings exist (grep -m1 returns first), (2) format is inconsistent (varying spacing), (3) plan has a different structure. Mitigation: Document title format requirement. Consider making this extraction more explicit in the agent (e.g., dedicated field in the output for title extraction confirmation).

**Risk: Incomplete migration**: If save-raw-plan.md also consumes agent output but changes are incomplete, one path works and the other doesn't. Mitigation: Update both save-plan.md and save-raw-plan.md together. Test both code paths.

**Risk: Markdown parsing doesn't handle edge cases**: Parent command parsing assumes specific markdown structure. If agent produces valid markdown but with unexpected structure (extra blank lines, different heading levels), parent parsing may fail. Mitigation: Make agent output structure strict and document it. Add basic validation in parent command before parsing.

**Risk: Removing JSON structure eliminates future extensibility**: If future requirements need to add more metadata to agent output (e.g., validation warnings, extraction confidence scores), markdown structure is harder to extend than JSON. Mitigation: Document this trade-off. If extensibility becomes important, can always revert to JSON with better field consumption in parent commands.

</details>
<!-- /erk:metadata-block:plan-body -->