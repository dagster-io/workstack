---
description: Generate commit message from diff file (pure text, no side effects)
argument-hint: <diff-file-path>
---

# Generate Commit Message

Read a diff file and generate a commit message based on its contents.

## Usage

```bash
/gt:generate-commit-message /tmp/diff-123.txt
```

## Input

The argument is a path to a temporary file containing:

- `Branch: <name>` - Current branch name
- `Parent: <name>` - Parent branch name
- Full diff output

## Output

Returns ONLY the commit message text - no other output.

## Implementation

Delegate to the gt-commit-message-generator agent:

```
Task(
    subagent_type="gt-commit-message-generator",
    description="Generate commit message",
    prompt="Read the diff file at <diff-file-path> and generate a commit message. Return ONLY the commit message text."
)
```

The agent reads the diff file and returns a structured commit message.
