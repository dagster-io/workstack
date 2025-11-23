## Fix gh issue create compatibility issue

**Problem:** `RealGitHubIssues.create_issue()` uses unsupported `--json` and `--jq` flags with `gh issue create`, causing "unknown flag: --json" error.

**Root cause:** Line 145 in `packages/erk-shared/src/erk_shared/github/issues.py`

**Fix:**

1. Remove `--json` and `--jq` flags from `gh issue create` command
2. Parse issue number from the URL that gh returns (format: `https://github.com/owner/repo/issues/123`)
3. Extract the number using string split or regex

**Implementation:**

- File: `packages/erk-shared/src/erk_shared/github/issues.py`
- Method: `RealGitHubIssues.create_issue()` (lines 136-148)
- Change command construction and parsing logic

**Testing:**

- Run existing unit tests to ensure behavior unchanged
- Test with actual gh CLI to verify issue creation works
