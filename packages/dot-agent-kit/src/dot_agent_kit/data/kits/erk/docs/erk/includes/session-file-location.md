# Session File Location

**Session file location:**

- Base: `~/.claude/projects/`
- Project directory: Working directory path with `/` replaced by `-` and prepended with `-`
- Example: `/Users/user/code/myproject` → `~/.claude/projects/-Users-user-code-myproject/`

**Plan extraction:**

- Parses JSONL files (one JSON object per line)
- Looks for `type: "tool_use"` with `name: "ExitPlanMode"`
- Extracts `input.plan` field
- Sorts by timestamp to find latest
