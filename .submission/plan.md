---
enriched_by_persist_plan: true
---

# Add "Work Me" Tagline to README

## Objective

Add a motivational subtitle "Work Me: Your parallel development companion" to the README.md file, positioned directly below the main title to provide friendly, accessible branding alongside the technical description.

## Context & Understanding

### Architectural Insights

- **README structure**: The README follows a clear hierarchy with the main title, technical tagline, and then introduction paragraphs explaining the problem and solution
- **Design intent**: Adding a subtitle maintains the existing structure while adding a layer of approachability without replacing the technical accuracy

### Domain Logic & Business Rules

- **Branding consistency**: The "Work Me" tagline was previously explored in a branch (`add-tagline-work-me-25-11-21`) that was created and deleted, suggesting this is a refinement of earlier branding work
- **Tone balance**: The README currently leads with technical terminology ("Git worktree manager designed for parallelized, plan-oriented, agentic engineering workflows") - adding "Work Me" provides a friendlier entry point for new users

### Complex Reasoning

**Rejected**: Replace the existing technical tagline
- Reason: The technical description is valuable for developers searching for worktree management solutions
- Would lose SEO value and clarity about what erk actually does

**Rejected**: Create a new "## Work Me" section
- Reason: Would interrupt the natural flow from title → introduction → features
- Adds unnecessary structural complexity for a simple tagline

**Chosen**: Add as subtitle below title
- Preserves technical description for searchability
- Adds approachable branding without disrupting flow
- Follows common README pattern of title + subtitle + description

### Known Pitfalls

- DO NOT remove or replace the existing technical tagline - it serves an important informational purpose
- DO NOT add formatting that breaks the visual hierarchy (the subtitle should be clearly secondary to the main technical description)

### Raw Discoveries Log

- Discovered: Git history shows branch `add-tagline-work-me-25-11-21` was created and deleted without merging
- Confirmed: No existing "Work Me" references in current codebase
- Verified: README.md is at repository root
- Noted: Current tagline is on line 3 (after title and blank line)
- Observed: README uses standard markdown formatting throughout

### Planning Artifacts

**Current README Structure (lines 1-14):**
```markdown
# erk

Git worktree manager designed for parallelized, plan-oriented, agentic engineering workflows.

Erk enables true parallel development by managing multiple worktrees with isolated working directories...
```

**Target structure after change:**
```markdown
# erk

**Work Me: Your parallel development companion**

Git worktree manager designed for parallelized, plan-oriented, agentic engineering workflows.

Erk enables true parallel development by managing multiple worktrees...
```

### Implementation Risks

**Technical Debt:**
- None identified - this is a simple content addition

**Uncertainty Areas:**
- None - the change is straightforward and localized

**Performance Concerns:**
- None - markdown files have no performance implications

**Security Considerations:**
- None - this is documentation only

## Implementation Steps

1. **Read README.md**: Read the current README to verify structure and locate insertion point
   - Success: Can see lines 1-15 containing title and current tagline
   - On failure: Verify file exists at `/Users/schrockn/code/erk/README.md`

   Related Context:
   - README structure confirmed during planning (see Planning Artifacts)
   - Title is on line 1, blank line 2, technical tagline line 3

2. **Add subtitle using Edit tool**: Insert the "Work Me" tagline between the title and technical description in `README.md`
   - Use Edit tool to add the subtitle as a new line after the title
   - Format as: `**Work Me: Your parallel development companion**` (bold markdown)
   - Add blank line before and after for proper spacing
   - Success: New tagline appears between title and technical description
   - On failure: Check that line numbers haven't shifted, re-read file

   Related Context:
   - Using bold (**) instead of heading (#) maintains proper hierarchy (see Complex Reasoning)
   - Preserving existing technical tagline for SEO and clarity (see Known Pitfalls)

3. **Verify formatting**: Read the updated section to ensure proper markdown rendering
   - Confirm blank lines for proper spacing
   - Verify bold formatting is correct
   - Success: Section reads cleanly with clear visual hierarchy
   - On failure: Adjust spacing or formatting as needed

   Related Context:
   - Markdown formatting conventions observed in current README (see Raw Discoveries Log)

## Testing

Testing is integrated within implementation steps above. Final validation:

- Visual review: Ensure hierarchy is clear (title > subtitle > technical description)
- Formatting check: Verify markdown renders correctly
- No CI validation needed (documentation-only change)

---

## Progress Tracking

**Current Status:** Plan created, ready for implementation - triggering CI

**Last Updated:** 2025-11-21 (CI trigger)

### Implementation Progress

- [ ] Step 1: Read README.md to verify structure and locate insertion point
- [ ] Step 2: Add subtitle using Edit tool to insert "Work Me" tagline
- [ ] Step 3: Verify formatting and proper markdown rendering

### Overall Progress

**Steps Completed:** 0 / 3
