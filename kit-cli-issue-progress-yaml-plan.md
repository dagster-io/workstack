---
erk_plan: true
---

# Implementation Plan: Kit CLI Progress Comments with Structured YAML

## Objective

Move GitHub issue progress comment posting from inline agent instructions (80+ lines) to testable Python kit CLI commands using the Kit CLI Push Down pattern. Comments will use collapsible `<details>` sections with structured YAML for machine-parsable progress data, while maintaining brief human-readable summaries.

## Context & Understanding

### Architectural Insights

**Why Kit CLI Push Down Pattern:**

- Agent markdown instructions are hard to test (no unit test framework)
- Inline bash/Python requires permission approvals for execution
- Mechanical computation (JSON parsing, string formatting) is error-prone in prompts
- Increases token usage unnecessarily (code + error handling in prompt)
- Not reusable across agents

**Chosen Pattern:**

- Push mechanical operations down to Python kit CLI commands
- Return structured JSON for agent consumption
- Fully testable with pytest
- Run without permission prompts (when allowlisted)
- Reduce token usage by ~80 lines in agent prompt

**Why Structured YAML in Comments:**

- Machine-parsable progress data (not reliant on markdown parsing)
- Collapsible by default (doesn't clutter issue view)
- Brief human-readable summary still visible
- Future tools can reliably parse progress state
- User preference: `<details>` with `<code>` summary label

### API/Tool Quirks

**GitHub Issues API:**

- `add_comment()` requires repo root path and issue number
- API failures should not block implementation (graceful degradation)
- Comments are idempotent (re-posting same comment is safe)

**Plan Folder Structure:**

- `.plan/issue.json` contains `{"issue_number": N, "issue_url": "..."}`
- `.plan/progress.md` has YAML front matter with `completed_steps` and `total_steps`
- Both files optional (commands must handle absence gracefully)

**Comment Format Pattern:**

- User-specified: Use `<details>` with `<summary><code>label</code></summary>` structure
- Summary label: `erk-implementation-status` (unified for both progress and completion)
- Human-readable text appears OUTSIDE the `<details>` section
- YAML code block INSIDE `<details>` contains all machine-parsable data

### Domain Logic & Business Rules

**Progress Tracking Requirements:**

- Progress comments should post after each implementation phase
- Completion comment should post when plan finishes
- If issue tracking not enabled (no `.plan/issue.json`), commands return success without posting
- If GitHub API fails, commands return error but don't crash
- Implementation must NEVER block on comment posting failures

**Comment Field Requirements:**

**Progress comments include:**

- `status: in_progress`
- `completed_steps`, `total_steps`, `percentage`
- `step_description` (the step just completed)
- `timestamp` (ISO format)

**Completion comments include:**

- `status: complete`
- `completed_steps`, `total_steps` (both should equal total)
- `summary` (brief implementation summary)
- `timestamp` (ISO format)

### Complex Reasoning

**Rejected: Inline Python in Agent Markdown**

- Reason: Agents generate Python code unreliably (syntax errors, import issues)
- Also: No test coverage, changes require markdown edits

**Rejected: Agent-level Error Handling**

- Reason: Agents handle errors inconsistently
- Also: Adds complexity to agent logic

**Rejected: Plain Markdown Comments**

- Reason: Parsing markdown for progress data is fragile
- Also: No reliable way to extract structured information

**Chosen: Kit CLI Commands with Structured YAML in Details**

- Commands format comments with `<details>` + YAML
- Brief human text visible, full data in collapsible section
- Agent uses `2>/dev/null || true` for graceful degradation
- All edge cases tested in Python unit tests
- YAML parsing is reliable and machine-friendly

### Known Pitfalls

**DO NOT make commands fail when `.plan/issue.json` missing:**

- Missing issue reference is normal for non-issue worktrees
- Return `{"success": false, "error_type": "no_issue_reference"}` but exit 0
- This allows `|| true` pattern to work correctly

**DO NOT use `ctx.issues` directly in kit CLI commands:**

- Kit CLI commands are standalone Python scripts
- Must create `RealGitHubIssues()` instance directly
- Context objects (`ErkContext`) don't exist in kit CLI layer

**DO NOT block on GitHub API failures:**

- Network issues, rate limits, auth problems should return errors
- Implementation must continue regardless
- Use try/except around `add_comment()` calls

**DO NOT forget to escape YAML special characters in user-provided strings:**

- Step descriptions and summaries may contain: colons, quotes, newlines
- Use YAML scalar literals (`|` or `>`) or proper quoting
- Example: `step_description: "Phase 1: Create abstraction"` (quotes protect colon)

**DO NOT use markdown backticks inside YAML strings:**

- YAML is inside a markdown code block already
- Backticks in YAML strings will break the markdown rendering
- Use plain text or YAML-appropriate escaping

### Raw Discoveries Log

- Confirmed: `read_issue_reference()` exists in `erk.core.plan_folder`
- Confirmed: `parse_progress_frontmatter()` exists in `erk.core.plan_folder`
- Verified: `RealGitHubIssues` can be imported from `erk.core.github.issues`
- Learned: Kit CLI commands registered in `kit.yaml` under `kit_cli_commands`
- Checked: Existing kit CLI command pattern in `comment_worktree_creation.py`
- Noted: All kit CLI commands use Click for argument parsing
- Verified: JSON output pattern uses dataclasses with `asdict()`
- Found: Test pattern uses `FakeGitHubIssues` for unit tests
- Discovered: Commands should use `git rev-parse --show-toplevel` for repo root
- User preference: Summary label is `erk-implementation-status` (not `erk-plan`)
- User preference: Brief text outside `<details>`, YAML inside
- User preference: All progress fields include timestamp and status indicators
- Learned: datetime.now(UTC).isoformat() produces ISO format timestamps

### Planning Artifacts

**Commands Run:**

- None (planning only)

**Code Examined:**

- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/comment_worktree_creation.py` (88 lines) - Reference implementation
- `.claude/commands/erk/implement-plan.md` (lines 139-159, 212-230, 330-350) - Current instructions
- `src/erk/core/plan_folder.py` (lines 320-396) - Plan folder utilities
- `src/erk/core/github/issues.py` - GitHub issues interface
- `docs/agentic-engineering-patterns/kit-cli-push-down.md` - Pattern documentation

**Referenced Patterns:**

- Kit CLI Push Down pattern (mechanical computation → Python)
- Fake-driven testing (FakeGitHubIssues for unit tests)
- Structured JSON output (dataclasses for consistency)
- User-specified comment format (details + YAML pattern)

**Example Comment Formats:**

**Progress Comment:**

````markdown
✓ Step 3/5 completed

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: in_progress
completed_steps: 3
total_steps: 5
percentage: 60
step_description: "Phase 1: Create abstraction"
timestamp: 2025-11-22T18:34:36Z
```
````

</details>
```

**Completion Comment:**

````markdown
✅ Implementation complete

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: 5
total_steps: 5
summary: "Added progress tracking with structured YAML comments"
timestamp: 2025-11-22T18:45:12Z
```
````

</details>
```

### Implementation Risks

**Technical Debt:**

- Current inline instructions have no test coverage
- Changes require editing 3 separate sections of markdown

**Uncertainty Areas:**

- Not sure if `git rev-parse` works in all environments (resolved: it's standard)
- Unclear if permission allowlist includes new commands (will need to add)
- YAML escaping complexity for user-provided strings (mitigated by quoting strategy)

**Performance Concerns:**

- None - commands execute quickly (JSON parsing + GitHub API call)

## Implementation Steps

### Phase 1: Create Progress Comment Command

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py`

1. **Create command structure:**
   - Import: `click`, `json`, `dataclass`, `asdict`, `subprocess`, `Path`, `datetime`
   - Import: `read_issue_reference`, `parse_progress_frontmatter` from `erk.core.plan_folder`
   - Import: `RealGitHubIssues` from `erk.core.github.issues`
   - Import: `UTC` from `datetime`
   - Define dataclasses: `ProgressSuccess`, `ProgressError`
   - Create Click command: `@click.command(name="post-progress-comment")`
   - Add option: `@click.option("--step-description", required=True)`

   Related Context:
   - Uses Kit CLI Push Down pattern (see Architectural Insights)
   - Follows existing command pattern from `comment_worktree_creation.py`

2. **Implement repo root detection:**
   Use LBYL pattern to check git command success:

   ```python
   result = subprocess.run(
       ["git", "rev-parse", "--show-toplevel"],
       capture_output=True, text=True, check=False
   )
   if result.returncode != 0:
       return ProgressError(error_type="not_in_repo", message="...")
   repo_root = Path(result.stdout.strip())
   ```

   Related Context:
   - Must use LBYL pattern (check returncode, not try/except)
   - See Known Pitfalls for error handling approach

3. **Read issue reference:**

   ```python
   plan_dir = Path.cwd() / ".plan"
   issue_ref = read_issue_reference(plan_dir)
   if issue_ref is None:
       return ProgressError(error_type="no_issue_reference", message="...")
   ```

   Related Context:
   - Missing issue reference is normal, not an error (see Known Pitfalls)
   - Command should exit 0 even when returning error

4. **Read progress front matter:**
   Check file exists before reading, then parse YAML front matter:

   ```python
   progress_file = plan_dir / "progress.md"
   if not progress_file.exists():
       return ProgressError(error_type="no_progress_file", message="...")

   content = progress_file.read_text(encoding="utf-8")
   frontmatter = parse_progress_frontmatter(content)
   if frontmatter is None:
       return ProgressError(error_type="invalid_progress_format", message="...")

   completed = frontmatter["completed_steps"]
   total = frontmatter["total_steps"]
   percentage = int((completed / total) * 100) if total > 0 else 0
   ```

   Related Context:
   - Progress file has YAML front matter (see API/Tool Quirks)
   - Must check file exists before reading (LBYL)

5. **Format comment with details + YAML:**
   [CRITICAL: Escape YAML special characters in step_description with quotes]

   Create brief human text + collapsible details section:

   ```python
   from datetime import UTC, datetime

   timestamp = datetime.now(UTC).isoformat()

   # Escape step_description for YAML (wrap in quotes to protect colons/special chars)
   yaml_safe_description = step_description.replace('"', '\\"')

   comment_body = f'''✓ Step {completed}/{total} completed
   ```

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: in_progress
completed_steps: { completed }
total_steps: { total }
percentage: { percentage }
step_description: "{yaml_safe_description}"
timestamp: { timestamp }
```

</details>'''
   ```

Related Context:

- User-specified format: brief text outside, YAML inside details
- Summary label: `erk-implementation-status`
- All required progress fields included (see Domain Logic)
- YAML escaping prevents rendering issues (see Known Pitfalls)

6. **Post comment and return result:**

   ```python
   try:
       github = RealGitHubIssues()
       github.add_comment(repo_root, issue_ref.issue_number, comment_body)
       return ProgressSuccess(
           success=True,
           issue_number=issue_ref.issue_number,
           progress=f"{completed}/{total} ({percentage}%)"
       )
   except RuntimeError as e:
       return ProgressError(error_type="github_api_failed", message=str(e))
   ```

   Related Context:
   - Must create `RealGitHubIssues()` directly, not use context (see Known Pitfalls)
   - GitHub API failures should return error, not crash (see Domain Logic)

7. **Return JSON output:**

   ```python
   click.echo(json.dumps(asdict(result), indent=2))
   if isinstance(result, ProgressError):
       raise SystemExit(0)  # Exit 0 even on error
   ```

   Related Context:
   - Exit 0 allows `|| true` pattern to work (see Complex Reasoning)

### Phase 2: Create Completion Comment Command

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/post_completion_comment.py`

1. **Create command structure** (same pattern as progress command):
   - Same imports as progress command
   - Define dataclasses: `CompletionSuccess`, `CompletionError`
   - Add option: `@click.option("--summary", required=True)`

2. **Implement repo root, issue reference, and progress reading** (identical to progress command)

3. **Verify completion status:**

   ```python
   if frontmatter["completed_steps"] != frontmatter["total_steps"]:
       return CompletionError(
           error_type="not_complete",
           message=f"Plan not finished: {completed}/{total} steps"
       )
   ```

   Related Context:
   - Completion comment should only post when 100% complete

4. **Format completion comment with details + YAML:**
   [CRITICAL: Escape YAML special characters in summary with quotes]

   ```python
   timestamp = datetime.now(UTC).isoformat()
   yaml_safe_summary = summary.replace('"', '\\"')

   comment_body = f'''✅ Implementation complete
   ```

<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: { total }
total_steps: { total }
summary: "{yaml_safe_summary}"
timestamp: { timestamp }
```

</details>'''
   ```

Related Context:

- Same format pattern as progress (see Architectural Insights)
- All required completion fields included (see Domain Logic)
- YAML escaping for user-provided summary

5. **Post comment and return result** (same try/except pattern as progress command)

6. **Return JSON output** (same pattern as progress command)

### Phase 3: Write Unit Tests for Progress Command

**File:** `packages/dot-agent-kit/tests/unit/kits/erk/test_post_progress_comment.py`

1. **Test success case:**
   - Create temp directory with `.plan/issue.json` and `.plan/progress.md`
   - Mock `git rev-parse` to return temp dir
   - Use `FakeGitHubIssues` to capture posted comment
   - Verify JSON output: `{"success": true, "issue_number": 123, "progress": "3/5 (60%)"}`
   - Verify comment contains: brief text, `<details>` section, YAML code block
   - Parse YAML from comment and verify all fields (status, completed_steps, total_steps, percentage, step_description, timestamp)
   - Verify exit code 0

   Related Context:
   - Uses fake-driven testing pattern (see Planning Artifacts)
   - Must validate YAML structure for machine parseability
   - Tests should parse the YAML to ensure it's valid

2. **Test no issue reference:**
   - Create temp directory without `.plan/issue.json`
   - Verify error JSON: `{"success": false, "error_type": "no_issue_reference", ...}`
   - Verify exit code 0 (not failure)

   Related Context:
   - Missing issue reference is normal (see Known Pitfalls)

3. **Test no progress file:**
   - Create temp directory with issue.json but no progress.md
   - Verify error JSON with `error_type: "no_progress_file"`

4. **Test invalid progress format:**
   - Create progress.md with malformed YAML front matter
   - Verify error JSON with `error_type: "invalid_progress_format"`

5. **Test not in git repo:**
   - Mock `git rev-parse` to fail (returncode != 0)
   - Verify error JSON with `error_type: "not_in_repo"`

6. **Test GitHub API failure:**
   - Use `FakeGitHubIssues` configured to raise `RuntimeError`
   - Verify error JSON with `error_type: "github_api_failed"`
   - Verify error message includes API error details

7. **Test edge cases:**
   - 0% progress (0/5 steps)
   - 50% progress (3/6 steps)
   - 100% progress (5/5 steps) - should succeed (not completion command)
   - Unicode in step description: "✓ Phase 1: Create façade"
   - Step description with colon: "Phase 1: Create API" (tests YAML escaping)
   - Step description with quotes: 'Fix "broken" feature' (tests escaping)

8. **Test YAML parseability:**
   - For success cases, extract YAML from comment body
   - Parse with `yaml.safe_load()`
   - Verify all required fields present and have correct types
   - Verify timestamp is valid ISO format

   Related Context:
   - Validates that YAML is machine-parsable (see Architectural Insights)
   - Ensures escaping doesn't break YAML structure

### Phase 4: Write Unit Tests for Completion Command

**File:** `packages/dot-agent-kit/tests/unit/kits/erk/test_post_completion_comment.py`

1. **Test success case:**
   - Create temp directory with 100% complete progress (5/5 steps)
   - Verify completion comment format (brief text + details + YAML)
   - Parse YAML and verify all completion fields (status, completed_steps, total_steps, summary, timestamp)
   - Verify summary included in YAML with proper escaping
   - Verify exit code 0

2. **Test not complete:**
   - Create temp directory with 60% complete progress (3/5 steps)
   - Verify error JSON with `error_type: "not_complete"`
   - Verify exit code 0

3. **Test other error cases** (same as progress command):
   - No issue reference
   - No progress file
   - Invalid progress format
   - Not in git repo
   - GitHub API failure

4. **Test YAML parseability:**
   - Extract and parse YAML from completion comment
   - Verify structure and field types
   - Test summary with special characters (colons, quotes)

5. **Test edge cases:**
   - Summary with Unicode: "Implémentation complète"
   - Summary with colon: "Summary: Complete feature"
   - Summary with quotes: "Added 'new' feature"

### Phase 5: Register Commands in Kit Manifest

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`

1. **Add command entries:**
   Append to `kit_cli_commands` section:

   ```yaml
   kit_cli_commands:
     # ... existing commands ...
     post-progress-comment:
       module: erk.post_progress_comment
       command: post_progress_comment
     post-completion-comment:
       module: erk.post_completion_comment
       command: post_completion_comment
   ```

   Related Context:
   - Follows existing command registration pattern
   - Module path relative to `kit_cli_commands/` directory

### Phase 6: Update Agent Command Instructions

**File:** `.claude/commands/erk/implement-plan.md`

1. **Simplify Step 2.6 (GitHub issue reference check):**

   Replace manual setup instructions with:

   ```markdown
   ### Step 2.6: Check for GitHub Issue Reference

   Progress tracking via GitHub comments is available if `.plan/issue.json` exists.
   The kit CLI commands handle all logic automatically - no manual setup required.
   ```

   Related Context:
   - Removes 20 lines of manual instructions
   - Reduces token usage in agent prompt

2. **Simplify Step 4 item 7 (post progress comment):**

   Replace manual comment posting with:

   ````markdown
   7. **Post progress comment to GitHub issue** (if enabled):
      ```bash
      dot-agent run erk post-progress-comment --step-description "Phase 1: Create abstraction" 2>/dev/null || true
      ```
   ````

   Note: Command fails silently if issue tracking not enabled. This is intentional.

   ```

   Related Context:
   - `2>/dev/null` suppresses error output
   - `|| true` ensures exit 0 (doesn't block implementation)
   - See Domain Logic for why failures must not block

   ```

3. **Simplify Step 7 item 5 (post completion comment):**

   Replace manual comment posting with:

   ````markdown
   5. **Post final completion comment to GitHub issue** (if enabled):
      ```bash
      dot-agent run erk post-completion-comment --summary "Brief implementation summary" 2>/dev/null || true
      ```
   ````

   Note: Command fails silently if issue tracking not enabled. This is intentional.

   ```

   Related Context:
   - Same error suppression pattern as progress command
   - Total reduction: 60+ lines of instructions removed
   ```

### Testing Strategy

All tests use **fake-driven testing** approach:

- Unit tests use `FakeGitHubIssues` (no real API calls)
- Create temporary directories with `.plan/` structure using `tmp_path` fixture
- Verify JSON output structure and content
- Validate error handling for all failure modes
- Test percentage calculation edge cases
- **Validate YAML parseability** - extract and parse YAML from comments
- Test YAML escaping for special characters (colons, quotes, newlines)
- No subprocess execution in unit tests (mock `git rev-parse`)

### Validation

After implementation:

1. Run unit tests: `/fast-ci`
2. Test commands manually:
   ```bash
   cd /tmp/test-worktree
   mkdir -p .plan
   echo '{"issue_number": 123, "issue_url": "...", "created_at": "...", "synced_at": "..."}' > .plan/issue.json
   echo '---\ncompleted_steps: 3\ntotal_steps: 5\n---' > .plan/progress.md
   dot-agent run erk post-progress-comment --step-description "Test phase"
   ```
3. Verify comment format:
   - Brief human-readable text visible
   - Details section collapses correctly
   - YAML parses successfully
4. Confirm agent command file reduced by ~80 lines

## Success Criteria

1. ✅ Kit CLI commands work standalone with correct JSON output
2. ✅ All unit tests pass with full edge case coverage
3. ✅ Comments use structured YAML in collapsible details sections
4. ✅ YAML is machine-parsable and contains all required fields
5. ✅ Agent command file simplified (80+ lines removed)
6. ✅ Progress tracking behavior unchanged (same comments at same times)
7. ✅ Failures gracefully degrade (implementation never blocked)
8. ✅ Commands added to permission allowlist (if needed)

---

## Progress Tracking

**Current Status:** Ready for implementation

**Last Updated:** 2025-11-22

### Implementation Progress

- [ ] Phase 1: Create progress comment command (`post_progress_comment.py`)
- [ ] Phase 2: Create completion comment command (`post_completion_comment.py`)
- [ ] Phase 3: Write unit tests for progress command (20+ test cases)
- [ ] Phase 4: Write unit tests for completion command (15+ test cases)
- [ ] Phase 5: Register commands in kit manifest (`kit.yaml`)
- [ ] Phase 6: Update agent command instructions (simplify 3 sections)

### Overall Progress

**Steps Completed:** 0 / 6
