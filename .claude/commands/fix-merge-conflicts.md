## <!-- https://motlin.com/blog/claude-code-utility-commands -->

🔀 Fix all merge conflicts and continue the git rebase.

- Check `git status` to understand the state of the rebase and identify conflicted files
- For each conflicted file:
  - Read the file to understand the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
  - Analyze what changes are in HEAD vs the incoming commit
  - Resolve conflicts by choosing the appropriate version or combining changes
  - Remove all conflict markers after resolution
- ✅ After resolving all conflicts:
  - If project memory includes a precommit check then run it and ensure no failures
  - Stage the resolved files with `git add`
  - Continue the rebase with `git rebase --continue`
- If the rebase continues with more conflicts, repeat the process
- ✔️ Verify successful completion by checking git status and recent commit history
