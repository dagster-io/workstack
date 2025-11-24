## Replace manual file check with Ensure.path_exists()

**Location**: `src/erk/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py:85-92`

**Changes**:
1. Replace the manual `if not progress_file.exists()` block with `Ensure.path_exists(ctx, progress_file, f"Progress file not found: {progress_file}")`
2. Remove the now-unused `ProgressError` dataclass import and definition (if it's only used for this error case)
3. Remove the `json` and `asdict` imports if they're only used for this error case
4. Note: Success responses will remain as JSON with `ProgressSuccess` dataclass (per clarification)

**Result**:
- Standardizes error handling with other erk commands as part of the Ensure expansion initiative (commit 1e241317)
- Error output changes from JSON to styled text: `Error: Progress file not found: /path/to/file`
- Exit code changes from 0 to 1 (standard error exit, breaking the || true pattern)
- Reduces code from 8 lines to 1 line
- Maintains JSON output for success cases to preserve machine-readable responses

## Context & Understanding

### Architectural Insights

- This change is part of Phase 3 of the Ensure expansion initiative (commit 1e241317), which standardizes error handling across the erk CLI
- The Ensure class provides context-aware path checking via `ctx.git.path_exists()`, which supports both real filesystem paths and test sentinel paths (crucial for testing)
- Design decision: Keep JSON output for success responses while migrating errors to styled text. This maintains backward compatibility for success cases while standardizing error presentation
- The `post_progress_comment` command is a specialized kit CLI command that currently returns JSON for all outcomes (success and error) - this will partially migrate to styled text for errors only

### Domain Logic & Business Rules

- Progress file (`progress.md` in `.impl/`) is a required artifact created earlier in the planning workflow
- The file must exist before progress can be posted - missing file indicates corrupted or incomplete planning state
- Progress tracking is critical to the implementation planning workflow, so errors here should be immediately visible (styled output, exit code 1)

### Known Pitfalls

- The current implementation exits with code 0 even on errors (line 81, 92) to support the `|| true` pattern. Switching to `Ensure.path_exists()` will exit with code 1, which breaks this graceful degradation pattern. Callers expecting exit code 0 will need to update their error handling
- The `ProgressError` and `ProgressSuccess` dataclasses are frozen=True, making them immutable - if any other code depends on these dataclasses for type hints or interface contracts, removing them could break those dependencies
- The command currently outputs machine-readable JSON for all responses. Styled text errors will break JSON parsers expecting consistent output format

### Complex Reasoning

- Alternative 1: Use Ensure for both success and error (fully standardized). Rejected because breaking JSON output for success would require coordinating with any consumers of ProgressSuccess
- Alternative 2: Create a wrapper that converts Ensure exceptions back to JSON ProgressError. Rejected because defeats the purpose of Ensure standardization
- Chosen approach: Replace only error path with Ensure, keep success as JSON. Balances standardization with minimal breaking changes
- The change trades full consistency for incremental migration - future refactoring could move success responses to styled output when consumers are identified and migrated

### Implementation Risks

- **Breaking change**: Exit code 0 → 1 for missing progress file. Any shell scripts using `|| true` pattern will stop masking errors
- **API change**: Removing ProgressError dataclass breaks any code that imports or type-hints against it
- **Output format inconsistency**: Error responses become plain text while success stays JSON. Consumers expecting JSON will fail on errors
- **Uncertainty**: Unclear if any external code depends on ProgressError/ProgressSuccess dataclasses or the exit code 0 pattern

### Raw Discoveries Log

- Ensure.path_exists() is defined in `src/erk/cli/ensure.py` (lines 66-100)
- Ensure class methods all use `user_output()` for styled output with red "Error: " prefix
- Path checking is delegated to `ctx.git.path_exists()` which supports test sentinels
- ProgressError and ProgressSuccess are frozen dataclasses (line 39, 48)
- Current code uses `json.dumps(asdict(result), indent=2)` pattern for all responses
- Ensure expansion was committed in 1e241317 with multiple other domain-specific methods added
- The kit_cli_commands directory has other commands like `create_issue.py` that use plain error messages via `click.echo(..., err=True)` (not Ensure)

### Planning Artifacts

- Examined: `src/erk/cli/ensure.py` (Ensure class implementation with path_exists method)
- Examined: `src/erk/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py` (current implementation at lines 85-92)
- Referenced: Ensure expansion commit 1e241317 and earlier path_exists simplification in commit 7f98344e
- Pattern check: Other kit commands like `create_issue.py` use click.echo for errors, not Ensure (architectural inconsistency)

### API/Tool Quirks

- Ensure.path_exists() requires ErkContext parameter (ctx.git.path_exists) - post_progress_comment receives click.Context, not ErkContext. The require_repo_root and require_github_issues context helpers are already used (lines 69, 132), so ctx is dot_agent_kit.Context with git integration
- The path_exists() method signature takes (ctx, path, error_message) where error_message is optional - requires passing explicit custom message for consistency with current error text
- ctx.git.path_exists() works with both real paths and test sentinel paths, making it safe for testing without mocking os.path

## Enrichment Summary

**Guidance Applied**: None provided

**Clarifications**: User confirmed that success responses should remain as JSON (ProgressSuccess dataclass), while only error responses are converted to styled text via Ensure

**Key Decision Points**:
1. This is incremental standardization - part of broader Ensure migration (1e241317)
2. Exit code changes from 0 to 1, which is a breaking change for callers using `|| true` pattern
3. Partial JSON → styled text conversion may create output format inconsistency
4. Must verify no external dependencies on ProgressError/ProgressSuccess dataclasses before removal
