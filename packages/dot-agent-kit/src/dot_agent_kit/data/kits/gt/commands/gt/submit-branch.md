---
description: Create git commit and submit current branch with Graphite
argument-hint: <description>
---

# Submit Branch

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

## What This Command Does

1. **Commit outstanding changes**: Stage and commit any uncommitted changes with a temporary message
2. **Squash commits**: Run `gt squash` to combine all commits in the current branch
3. **Analyze and update message**: Use git-diff-summarizer agent to analyze all changes and create a comprehensive commit message
4. **Submit branch**: Run `gt submit --publish` to create/update PR for the current branch
5. **Update PR metadata**: If PR already exists, sync PR title and body with the new commit message
6. **Report results**: Show the submitted PRs and their URLs

## Usage

```bash
# With description argument
/gt:submit-branch "Add user authentication feature"

# Without argument (will analyze changes automatically)
/gt:submit-branch
```

## Agent Invocation

**ALWAYS delegate to the branch-submitter agent:**

```
Task(
    subagent_type="gt:branch-submitter",
    description="Submit branch with gt workflow",
    prompt="Execute complete gt submit workflow. Description argument: '<user-provided-description or None>'"
)
```

The agent will handle all steps and return a summary:

- Committing outstanding changes
- Squashing commits
- Analyzing changes with git-diff-summarizer
- Creating comprehensive commit message
- Submitting branch with `gt submit`
- Updating PR metadata if PR exists
- Reporting results

## Expected Output

The agent will return a structured summary:

```
## ✅ Branch Submitted Successfully

- **PR Created/Updated**: #[number]
- **URL**: [full PR URL]
- **Branch**: [branch name]
```

Or on failure:

```
## ❌ Submission Failed

**Failed at**: [step name]
**Error**: [error message]
**Next steps**: [what user should do to resolve]
```

## Important Notes

- **All implementation** is handled by the branch-submitter agent
- **Context optimization**: 270+ lines of implementation stay in subagent context
- **Cost efficiency**: Subagent can use Haiku model for git/Graphite operations
- **Reusability**: Agent can be invoked from other workflows
