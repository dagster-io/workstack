# Make Issue/PR Numbers Consistently Linkable in CLI Output

## Overview

Standardize issue and PR number display across all CLI commands to be consistently clickable using terminal hyperlinks. The codebase already has OSC 8 hyperlink infrastructure in some places but applies it inconsistently. This plan extends the existing patterns to all locations where issue/PR numbers are displayed.

## Context & Understanding

### Current State

- **Existing Infrastructure**: OSC 8 hyperlink support already implemented in `format_pr_info()` (src/erk/core/display_utils.py:63-94) and `format_plan_display()` (src/erk/core/display_utils.py:233-274)
- **Inconsistency Problem**: List commands show clickable PR numbers, but status renderer and other commands show plain text with separate URL lines
- **Mixed Output Libraries**:
  - Click used for color styling (`click.style(text, fg="cyan")`)
  - Rich used for tables in `plan/list_cmd.py`
  - Different hyperlink syntaxes required: OSC 8 for Click, Rich markup for Rich tables

### Technical Details

- **OSC 8 Format**: `\033]8;;{url}\033\\{colored_text}\033]8;;\033\\`
- **Rich Markup Format**: `[link={url}][cyan]#{number}[/cyan][/link]`
- **Color Convention**: Cyan = clickable links (vs bright_blue for non-clickable indicators) - see display_utils.py:86-87
- **Visual Length**: `get_visible_length()` (display_utils.py:14-27) already handles OSC 8 sequences for proper alignment

### URL Construction Patterns

- **Issue URLs**: `https://github.com/{owner}/{repo}/issues/{number}` (from `IssueInfo.url`)
- **PR GitHub URLs**: `https://github.com/{owner}/{repo}/pull/{number}` (from `PullRequestInfo.url`)
- **PR Graphite URLs**: `https://app.graphite.com/github/pr/{owner}/{repo}/{number}` (via `ctx.graphite.get_graphite_url()`)
- **Conversion**: `_graphite_url_to_github_url()` exists but we're going opposite direction

### User Preferences

- PR links → Graphite URLs (for stack visualization features)
- Remove duplicate URL lines from status output (cleaner, since numbers are clickable)
- Rich tables → Use Rich markup syntax (native rendering)
- Create utility functions to reduce code duplication

### Locations Needing Updates

**Already Linked:**

- ✅ `display_utils.py::format_pr_info()` - PR numbers with Graphite URLs
- ✅ `display_utils.py::format_plan_display()` - Issue numbers with GitHub URLs

**Plain Text (Need Linking):**

- ❌ `status/renderers/simple.py:164` - Issue numbers (has URL available)
- ❌ `status/renderers/simple.py:233` - PR numbers (has URL available)
- ❌ `cli/commands/submit.py:80` - Issue numbers (has issue.url)
- ❌ `cli/commands/land_stack/execution.py` - PR numbers (need URL access)
- ❌ `cli/commands/land_stack/display.py` - PR numbers (need URL access)
- ❌ `cli/commands/plan/list_cmd.py:178` - Issue numbers in Rich table

## Implementation Steps

### 1. Create Utility Functions in display_utils.py

Add three reusable functions to reduce duplication:

```python
def format_clickable_issue(number: int, url: str) -> str:
    """Format an issue number as a clickable hyperlink.

    Args:
        number: The issue number
        url: The GitHub issue URL

    Returns:
        OSC 8 hyperlinked issue number in cyan
    """
    issue_text = f"#{number}"
    colored_text = click.style(issue_text, fg="cyan")
    return f"\033]8;;{url}\033\\{colored_text}\033]8;;\033\\"


def format_clickable_pr(number: int, url: str, use_graphite: bool = True) -> str:
    """Format a PR number as a clickable hyperlink.

    Args:
        number: The PR number
        url: The PR URL (GitHub or Graphite)
        use_graphite: If True and URL is GitHub, convert to Graphite URL

    Returns:
        OSC 8 hyperlinked PR number in cyan
    """
    # Convert GitHub URL to Graphite if requested
    if use_graphite and "github.com" in url:
        # Parse: https://github.com/owner/repo/pull/123
        parts = url.rstrip('/').split('/')
        if len(parts) >= 5 and parts[-2] == 'pull':
            owner = parts[-4]
            repo = parts[-3]
            url = f"https://app.graphite.com/github/pr/{owner}/{repo}/{number}"

    pr_text = f"#{number}"
    colored_text = click.style(pr_text, fg="cyan")
    return f"\033]8;;{url}\033\\{colored_text}\033]8;;\033\\"


def format_clickable_issue_rich(number: int, url: str) -> str:
    """Format an issue number as a Rich markup hyperlink.

    Args:
        number: The issue number
        url: The GitHub issue URL

    Returns:
        Rich markup hyperlink string
    """
    return f"[link={url}][cyan]#{number}[/cyan][/link]"
```

**Context**: These utilities standardize hyperlink creation and make it easy to ensure consistency. The `use_graphite` parameter allows flexibility for contexts where Graphite URLs are preferred (default) vs GitHub URLs.

### 2. Refactor Existing Linked Displays

Update `format_pr_info()` and `format_plan_display()` to use new utilities:

**In `format_pr_info()` (lines 63-94):**

- Replace inline OSC 8 code (lines 84-88) with call to `format_clickable_pr(pr.number, graphite_url, use_graphite=True)`
- Keep fallback logic for when URL is unavailable

**In `format_plan_display()` (lines 233-274):**

- Replace inline OSC 8 code (lines 244-246) with call to `format_clickable_issue(plan_identifier, url)`
- Keep fallback logic for when URL is unavailable

**Context**: This reduces duplication and ensures consistency with the new utility functions.

### 3. Fix Status Renderer (status/renderers/simple.py)

**Issue Number Display (line 164):**

- Replace: `issue_text = click.style(f"#{status.plan.issue_number}", fg="cyan")`
- With: `issue_text = format_clickable_issue(status.plan.issue_number, status.plan.issue_url)`
- Remove line 168 (separate URL display): `user_output(click.style(f"  {status.plan.issue_url}", dim=True))`

**PR Number Display (line 233):**

- Replace: `pr_link = click.style(f"#{pr.number}", fg="cyan")`
- With: `pr_link = format_clickable_pr(pr.number, pr.url, use_graphite=True)`
- Remove line 256 (separate URL display): `user_output(click.style(f"    {pr.url}", dim=True))`

**Context**: Status renderer has URLs readily available, making this a straightforward replacement. Removing duplicate URL lines creates cleaner output since the numbers are now clickable.

### 4. Fix Submit Command (cli/commands/submit.py)

**Line 80:**

- Replace: `click.style(f'#{issue_number}', fg='cyan')`
- With: `format_clickable_issue(issue_number, issue.url)`

**Context**: Submit command already has `issue.url` available from GitHub CLI response, so this is a direct replacement.

### 5. Fix Land Stack Commands

**In land_stack/execution.py:**

- Locate PR number displays
- Ensure PR objects have `.url` field available
- Replace plain cyan styling with `format_clickable_pr(pr.number, pr.url, use_graphite=True)`

**In land_stack/display.py:**

- Locate PR number displays
- Ensure PR objects have `.url` field available
- Replace plain cyan styling with `format_clickable_pr(pr.number, pr.url, use_graphite=True)`

**Context**: These commands may need investigation to ensure PR URLs are available in the context. If not, may need to fetch them or pass them through from calling code.

### 6. Fix Plan List Command (cli/commands/plan/list_cmd.py)

**Line 178:**

- Replace: `issue_id = f"#{plan.plan_identifier}"`
- With: `issue_id = format_clickable_issue_rich(plan.plan_identifier, plan.url)` (assuming plan has URL)
- If plan object doesn't have URL, may need to construct it from repository context

**Context**: Rich tables require Rich markup syntax instead of OSC 8 sequences. The `format_clickable_issue_rich()` utility handles this difference.

### 7. Add Import Statements

Ensure all modified files import the new utility functions:

```python
from erk.core.display_utils import format_clickable_issue, format_clickable_pr, format_clickable_issue_rich
```

### 8. Test Changes

**Manual Testing:**

- Run `erk status` - verify issue/PR numbers are clickable, no duplicate URLs
- Run `erk plan list` - verify issue numbers are clickable in table
- Run `erk submit` (or mock workflow) - verify issue numbers are clickable
- Run land stack commands - verify PR numbers are clickable
- Test in multiple terminals (iTerm2, Terminal.app, VSCode terminal) to ensure compatibility

**Visual Verification:**

- Confirm cyan color consistency for all clickable numbers
- Verify alignment/formatting isn't broken (OSC 8 sequences should be invisible to `get_visible_length()`)
- Check that Graphite URLs are used for PRs (hover or click to verify)

**Edge Cases:**

- What happens when URL is unavailable? (Should fall back to plain cyan text)
- What happens in terminals that don't support OSC 8? (Should still show text, just not clickable)

## Implementation Risks

1. **URL Availability**: Some contexts might not have URLs readily available, requiring additional data plumbing or API calls
2. **Terminal Compatibility**: Not all terminals support OSC 8 hyperlinks (but graceful degradation is built-in)
3. **GitHub-to-Graphite Conversion**: URL parsing logic in `format_clickable_pr()` assumes standard GitHub URL format
4. **Rich Table Rendering**: Rich markup syntax may behave differently than expected in complex table layouts

## Success Criteria

- ✅ All issue numbers displayed in CLI are clickable hyperlinks to GitHub issues
- ✅ All PR numbers displayed in CLI are clickable hyperlinks to Graphite PR pages
- ✅ Status renderer no longer shows duplicate URL lines
- ✅ Cyan color consistently indicates clickable links across all commands
- ✅ Utility functions reduce code duplication
- ✅ Visual formatting/alignment remains correct
- ✅ Changes work in common terminal emulators
