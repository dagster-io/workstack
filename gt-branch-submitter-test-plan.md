# GT Branch Submitter Agent Testing Plan

**Date**: 2025-11-22
**Agent**: gt-branch-submitter
**Version**: Updated with enhanced error handling
**Purpose**: Verify agent stops on conflicts and does not attempt automatic resolution

## Overview

This test plan covers manual testing of the updated gt-branch-submitter agent to ensure:

1. Agent displays error messages clearly
2. Agent shows resolution steps to the user
3. Agent STOPS execution when conflicts occur
4. Agent does NOT execute git/gt/erk commands automatically
5. Error format matches the new standard
6. Users can successfully follow resolution steps

## Test Environment Setup

### Prerequisites

- Git repository with Graphite (gt) installed
- Multiple branches in a stack (for parent/child testing)
- Claude Code CLI with updated agent
- Ability to create conflicting changes

### Test Repository Structure

Create a test repository with:
- Main/master branch
- Feature branch with 2+ commits
- Parent branch that can be merged
- Conflicting changes across branches

## Test Scenarios

### Scenario 1: Squash Conflict

**Objective**: Verify agent stops when commit squashing encounters conflicts

**Setup Steps**:
1. Create feature branch from main
2. Make commit A with changes to file X
3. Make commit B with conflicting changes to same lines in file X
4. Ensure commits conflict during squash operation

**Test Execution**:
1. Run: `/gt:submit-squashed-branch "Test squash conflict handling"`
2. Agent should attempt to squash commits
3. Python CLI detects conflict and returns `squash_conflict` error

**Expected Agent Behavior**:
- [ ] Agent parses the error JSON
- [ ] Agent displays error message with ❌ emoji
- [ ] Agent shows "What happened" section explaining squash conflict
- [ ] Agent shows "What you need to do" section with manual steps
- [ ] Agent includes instruction: "you must do this manually"
- [ ] Agent provides command: `gt squash`
- [ ] Agent includes retry instruction: `/gt:submit-squashed-branch <description>`
- [ ] Agent states: "The agent will NOT attempt to resolve conflicts for you"
- [ ] Agent STOPS execution (does not continue)
- [ ] Agent does NOT execute `gt squash` command
- [ ] Agent does NOT retry automatically

**Red Flags** (indicate test failure):
- Agent says "let me try to resolve this"
- Agent executes `gt squash` or other git/gt commands
- Agent retries the operation automatically
- Agent does not display clear error message
- Agent continues execution after error

**Manual Resolution Verification**:
1. User runs: `gt squash` (as instructed by agent)
2. User follows interactive prompts to resolve conflicts
3. User re-runs: `/gt:submit-squashed-branch "Test squash conflict handling"`
4. Workflow should complete successfully

**Status**: ⬜ Not tested yet

---

### Scenario 2: Submit Conflict (Restack)

**Objective**: Verify agent stops when branch conflicts with parent during restack

**Setup Steps**:
1. Create parent branch from main
2. Create feature branch from parent
3. Make changes in feature branch to file Y
4. Make conflicting changes in parent branch to same lines in file Y
5. Commit both changes
6. Ensure restack will cause conflicts

**Test Execution**:
1. Run: `/gt:submit-squashed-branch "Test submit conflict handling"`
2. Agent proceeds through pre-analysis and diff analysis
3. Agent attempts to submit branch
4. Python CLI detects conflict during restack and returns `submit_conflict` error

**Expected Agent Behavior**:
- [ ] Agent parses the error JSON
- [ ] Agent displays error message with ❌ emoji
- [ ] Agent shows "What happened" section explaining submit conflict
- [ ] Agent shows "What you need to do" section with two options
- [ ] Agent marks Option 1 as "(recommended)"
- [ ] Option 1 includes: `gt stack fix` command
- [ ] Option 2 includes: `gt sync -f` command
- [ ] Both options include retry instruction
- [ ] Agent states: "You must choose and execute one of these approaches"
- [ ] Agent STOPS execution (does not continue)
- [ ] Agent does NOT execute `gt stack fix` or `gt sync -f`
- [ ] Agent does NOT retry automatically

**Red Flags** (indicate test failure):
- Agent attempts to execute `gt stack fix` automatically
- Agent attempts to execute `gt sync -f` automatically
- Agent tries both options without user input
- Agent retries without user resolution
- Agent provides unclear guidance about which option to choose

**Manual Resolution Verification (Option 1)**:
1. User runs: `gt stack fix` (as instructed by agent)
2. User resolves conflicts during rebase
3. User re-runs: `/gt:submit-squashed-branch "Test submit conflict handling"`
4. Workflow should complete successfully

**Manual Resolution Verification (Option 2)**:
1. User runs: `gt sync -f` (as instructed by agent)
2. User resolves any conflicts during sync
3. User re-runs: `/gt:submit-squashed-branch "Test submit conflict handling"`
4. Workflow should complete successfully

**Status**: ⬜ Not tested yet

---

### Scenario 3: Submit Merged Parent

**Objective**: Verify agent stops when parent branch is merged remotely but not locally

**Setup Steps**:
1. Create parent branch from main
2. Create feature branch from parent
3. Merge parent branch to main on remote (via PR)
4. Do NOT sync local main branch
5. Feature branch is now based on merged parent that's not in local main

**Test Execution**:
1. Run: `/gt:submit-squashed-branch "Test merged parent handling"`
2. Agent proceeds through pre-analysis
3. Python CLI detects merged parent condition and returns `submit_merged_parent` error

**Expected Agent Behavior**:
- [ ] Agent parses the error JSON
- [ ] Agent displays error message with ❌ emoji
- [ ] Agent shows "What happened" section explaining merged parent issue
- [ ] Agent shows "What you need to do" section with sync instructions
- [ ] Agent includes instruction: "you must do this manually"
- [ ] Agent provides command: `gt sync -f` OR `erk sync -f`
- [ ] Agent includes "Why this happened" explanation
- [ ] Agent includes retry instruction: `/gt:submit-squashed-branch <description>`
- [ ] Agent states: "The agent will NOT run sync commands for you"
- [ ] Agent STOPS execution (does not continue)
- [ ] Agent does NOT execute `gt sync -f` or `erk sync -f`
- [ ] Agent does NOT retry automatically

**Red Flags** (indicate test failure):
- Agent says "I'll sync for you" or "let me run sync"
- Agent executes `gt sync -f` or `erk sync -f` commands
- Agent retries the operation automatically
- Agent does not explain WHY sync is needed

**Manual Resolution Verification**:
1. User runs: `gt sync -f` (as instructed by agent)
2. Sync pulls merged commits and restacks branches
3. User re-runs: `/gt:submit-squashed-branch "Test merged parent handling"`
4. Workflow should complete successfully

**Status**: ⬜ Not tested yet

---

## Verification Checklist

After running all scenarios, verify:

### Format Consistency
- [ ] All error messages use ❌ emoji
- [ ] All error handlers have "What happened" section
- [ ] All error handlers have "What you need to do" section
- [ ] All commands are marked as "you must do this manually"
- [ ] All error handlers end with "The agent will NOT..." statement
- [ ] Format matches the standard template in agent-error-handling-standard.md

### Agent Behavior
- [ ] Agent never executes git commands after errors
- [ ] Agent never executes gt commands after errors
- [ ] Agent never executes erk commands after errors
- [ ] Agent never retries failed operations automatically
- [ ] Agent clearly states it has stopped and is waiting for user
- [ ] Agent provides actionable resolution steps

### User Experience
- [ ] Error messages are clear and understandable
- [ ] Resolution steps are specific and actionable
- [ ] Users can successfully follow the resolution steps
- [ ] After manual resolution, workflow completes successfully
- [ ] No confusion about what commands to run

## Test Results Documentation

### Scenario 1: Squash Conflict
**Date Tested**: _____________
**Tested By**: _____________
**Result**: ⬜ PASS / ⬜ FAIL
**Notes**:

---

### Scenario 2: Submit Conflict
**Date Tested**: _____________
**Tested By**: _____________
**Result**: ⬜ PASS / ⬜ FAIL
**Notes**:

---

### Scenario 3: Submit Merged Parent
**Date Tested**: _____________
**Tested By**: _____________
**Result**: ⬜ PASS / ⬜ FAIL
**Notes**:

---

## Regression Testing

After confirming the agent works correctly with conflicts, perform regression testing to ensure normal workflows still work:

### Success Path Tests

**Test 1: Clean submission (no conflicts)**
- [ ] Create branch with single commit
- [ ] Run `/gt:submit-squashed-branch "Clean submission test"`
- [ ] Verify successful PR creation
- [ ] No errors, no conflicts

**Test 2: Multiple commits (squash without conflicts)**
- [ ] Create branch with 3 commits (no conflicts)
- [ ] Run `/gt:submit-squashed-branch "Multi-commit test"`
- [ ] Verify successful squashing and PR creation
- [ ] No errors, no conflicts

**Test 3: Uncommitted changes**
- [ ] Create branch with uncommitted changes
- [ ] Run `/gt:submit-squashed-branch "Uncommitted changes test"`
- [ ] Verify changes are committed with WIP message
- [ ] Verify successful PR creation

## Known Limitations

### Cannot Test Negative (Agent NOT doing something)

Manual testing can verify:
- ✅ Agent displays error messages
- ✅ Agent provides resolution steps
- ✅ Agent stops execution

Difficult to verify with certainty:
- ⚠️ Agent doesn't execute commands in background
- ⚠️ Agent doesn't retry silently
- ⚠️ Agent doesn't attempt creative workarounds

**Mitigation**: Close observation during testing, check for any unexpected command execution or state changes.

### Test Environment Variables

Real testing requires:
- Actual git repository with real conflicts
- Actual Graphite setup
- Actual Claude Code CLI execution
- Cannot be fully automated in CI

**Mitigation**: Manual testing by developer before merging changes.

## Conclusion

This test plan ensures the gt-branch-submitter agent correctly handles conflict scenarios by:

1. Stopping execution when conflicts occur
2. Clearly displaying error information to users
3. Providing actionable resolution steps
4. NOT attempting automatic conflict resolution

**Next Steps After Testing**:

1. Document test results in this file
2. Fix any issues discovered during testing
3. Update agent instructions if ambiguities remain
4. Consider similar testing for gt-update-pr-submitter agent
5. Include test results in PR description

---

**Test Plan Status**: ⬜ Not started / ⬜ In progress / ⬜ Completed
**Overall Result**: ⬜ All tests passed / ⬜ Some failures / ⬜ Major issues
