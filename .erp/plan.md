# Fix: CI workflows not triggered after dispatch workflow

## Problem

PR #1400 has only CodeQL checks - no Test, Lint, or Type Check workflows ran.

## Root Cause

**GitHub's `GITHUB_TOKEN` does NOT trigger new workflow runs** - by design to prevent infinite loops.

The "Trigger CI workflows" step uses `git push` with the default token. Push events from `GITHUB_TOKEN` are ignored.

## Solution

Replace the empty commit push with explicit `gh workflow run` calls:

```yaml
- name: Trigger CI workflows
  if: steps.implement.outputs.implementation_success == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
    BRANCH_NAME: ${{ steps.branch_name.outputs.branch_name }}
  run: |
    # Trigger CI workflows explicitly via workflow_dispatch
    gh workflow run test.yml --ref "$BRANCH_NAME"
    gh workflow run lint.yml --ref "$BRANCH_NAME"
    gh workflow run pyright.yml --ref "$BRANCH_NAME"
    gh workflow run prettier.yml --ref "$BRANCH_NAME"
    gh workflow run check-sync.yml --ref "$BRANCH_NAME"
    gh workflow run md-check.yml --ref "$BRANCH_NAME"
    echo "✅ CI workflows triggered via workflow_dispatch"
```

## Files to Modify

1. `.github/workflows/dispatch-erk-queue-git.yml` - Replace push with workflow_dispatch
2. `.github/workflows/dispatch-erk-queue-single-job.yml` - Same fix
3. `.github/workflows/dispatch-erk-queue.yml` - Same fix

## Implementation

For each workflow file, replace the "Trigger CI workflows" step:

**Before:**
```yaml
- name: Trigger CI workflows
  if: steps.implement.outputs.implementation_success == 'true'
  env:
    BRANCH_NAME: ${{ steps.branch_name.outputs.branch_name }}
  run: |
    # Push empty commit to trigger CI
    git commit --allow-empty -m "Trigger CI workflows"
    git push origin "$BRANCH_NAME"
    echo "✅ CI workflows triggered"
```

**After:**
```yaml
- name: Trigger CI workflows
  if: steps.implement.outputs.implementation_success == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
    BRANCH_NAME: ${{ steps.branch_name.outputs.branch_name }}
  run: |
    # Trigger CI workflows explicitly (push events from GITHUB_TOKEN don't trigger workflows)
    gh workflow run test.yml --ref "$BRANCH_NAME"
    gh workflow run lint.yml --ref "$BRANCH_NAME"
    gh workflow run pyright.yml --ref "$BRANCH_NAME"
    gh workflow run prettier.yml --ref "$BRANCH_NAME"
    gh workflow run check-sync.yml --ref "$BRANCH_NAME"
    gh workflow run md-check.yml --ref "$BRANCH_NAME"
    echo "✅ CI workflows triggered via workflow_dispatch"
```

## Note on PR #1400

After this fix, PR #1400 still needs CI triggered manually:
```bash
gh workflow run test.yml --ref plan-use-ensure-in-navigation
gh workflow run lint.yml --ref plan-use-ensure-in-navigation
gh workflow run pyright.yml --ref plan-use-ensure-in-navigation
```