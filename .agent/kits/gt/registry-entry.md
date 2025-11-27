### gt (v0.1.0)

**Purpose**: Graphite stack management with landing and submission commands

**Artifacts**:

- agent: agents/gt/gt-commit-message-generator.md, agents/gt/gt-update-pr-submitter.md
- command: commands/gt/pr-submit.md, commands/gt/pr-update.md, commands/gt/generate-commit-message.md
- skill: skills/gt-graphite/SKILL.md, skills/gt-graphite/references/gt-reference.md

**Usage**:

- Use Task tool with subagent_type="gt-commit-message-generator" for commit message generation
- Run `/gt:pr-submit` command for PR submission
- Load `gt-graphite` skill for Graphite stack visualization and terminology
