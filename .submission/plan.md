---
erk_plan: true
created_at: 2025-11-21T19:30:00Z
---

# Make Erk Default Confirmation Yes

## Analysis

The code in `src/erk/cli/commands/init.py` **already has `default=True`** for all shell integration confirmation prompts:
- Line 117: "Show shell integration setup instructions?" → `default=True`
- Line 184: "Proceed with updating global config?" → `default=True`
- Line 313: "Proceed with updating global config?" → `default=True`

**This means the prompts should already default to "yes" (pressing Enter accepts).**

## Hypothesis

You may be experiencing one of these scenarios:
1. **Visual confusion**: Click's prompt shows `[Y/n]` for `default=True`, but it might not be visually obvious
2. **Old version**: You might be running an older version of erk where these were `default=False`
3. **Different confirmation**: You might be seeing a different confirmation prompt elsewhere

## Investigation Needed

Since the code already has the correct defaults, we need to:

1. **Verify current behavior** - Check if there are any other confirmation prompts related to shell setup that might have `default=False`
2. **Test actual behavior** - Run the actual command and observe which specific prompt is problematic
3. **Check version mismatch** - Verify the erk version you're running matches the code in the repo

## Possible Actions

If investigation reveals prompts that actually need changing:
1. Search for other `click.confirm` calls related to erk default/shell setup
2. Update any found prompts from `default=False` to `default=True`
3. Test the updated behavior
4. Update any related tests that validate the confirmation defaults
