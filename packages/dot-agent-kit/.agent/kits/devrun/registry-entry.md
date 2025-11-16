### devrun (v0.2.0)

**Purpose**: The devrun agent executes development CLI tools (pytest, pyright, ruff, prettier, make, gt) with specialized result parsing. The kit provides two-layer enforcement: passive reminders (UserPromptSubmit hook) and active blocking (PreToolUse hook) to ensure consistent usage.

**Capabilities**:

- **Active blocking**: PreToolUse hook prevents direct Bash usage of dev tools
- **Passive reminders**: UserPromptSubmit hook displays usage guidance
- **Specialized parsing**: Interprets tool output for test failures, type errors, linting issues
- **Consistent workflow**: Enforces devrun usage across all development tools

**Artifacts**:

- agent: agents/devrun/devrun.md
- doc: docs/devrun/tools/gt.md, docs/devrun/tools/make.md, docs/devrun/tools/prettier.md, docs/devrun/tools/pyright.md, docs/devrun/tools/pytest.md, docs/devrun/tools/ruff.md

**Usage**:

- Use Task tool with subagent_type="devrun"
