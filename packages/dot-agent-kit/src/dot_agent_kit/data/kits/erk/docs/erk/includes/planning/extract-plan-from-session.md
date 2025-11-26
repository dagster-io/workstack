# Extract Plan from Session Logs

Use the kit CLI to extract the plan from session logs:

```bash
# Extract plan using kit CLI
plan_result=$(dot-agent run erk save-plan-from-session --extract-only --format json 2>&1)
```

**Parse the result:**

```bash
# Check if extraction succeeded
if echo "$plan_result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS: Extract plan content and title
    plan_content=$(echo "$plan_result" | jq -r '.plan_content')
    plan_title=$(echo "$plan_result" | jq -r '.title')
else
    # FAILURE: Report error
    error_msg=$(echo "$plan_result" | jq -r '.error // "Unknown error"')
    echo "❌ Error: Failed to extract plan from session logs"
    echo "Details: $error_msg"
fi
```

**If no plan found in session logs:**

```
❌ Error: No plan found in session logs

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from session logs automatically.
```
