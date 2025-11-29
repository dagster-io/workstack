---
completed_steps: 0
total_steps: 14
---

# Progress Tracking

- [ ] 1. The command loader (`group.py:133`) converts command names to function names by replacing hyphens with underscores: `get-closing-text` → `get_closing_text`
- [ ] 2. The CLI file (`get_closing_text.py`) defines the function as `get_closing_text_cmd` (not `get_closing_text`)
- [ ] 3. This was done to avoid a naming collision with the imported canonical function `from erk_shared.impl_folder import get_closing_text`
- [ ] 1. **Name**: lowercase letters, numbers, hyphens only (`^[a-z][a-z0-9-]*$`)
- [ ] 2. **Path**: must end with `.py` and start with `kit_cli_commands/`
- [ ] 3. **Description**: non-empty string
- [ ] 4. **No directory traversal**: path cannot contain `..`
- [ ] 1. **"does not have expected function"** - Function name doesn't match command name (see naming convention above)
- [ ] 2. **"Command file not found"** - Path in kit.yaml doesn't exist
- [ ] 3. **"Failed to import command"** - Python import error in the command file
- [ ] 4. **"Invalid command"** - Validation error (name format, path, description)
- [ ] 1. Run `dot-agent run erk --help` - should list commands without warnings
- [ ] 2. Run `dot-agent run erk get-closing-text` in a worktree with `.impl/issue.json` - should output closing text
- [ ] 3. Run `dot-agent run erk get-closing-text` in a directory without `.impl/issue.json` - should have no output
