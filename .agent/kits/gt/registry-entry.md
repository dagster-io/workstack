### gt (v0.1.0)

**Purpose**: Graphite stack management with landing and submission commands

**Artifacts**:

- agent: agents/gt/gt-branch-submitter.md
- command: commands/gt/submit-branch.md, commands/gt/update-pr.md
- skill: skills/gt-graphite/SKILL.md, skills/gt-graphite/references/gt-reference.md

**Usage**:

- Use Task tool with subagent_type="gt-branch-submitter" for branch submission workflow
- Run `/gt:submit-branch` command to create PRs
- Run `/gt:update-pr` command to update existing PRs
- Load `gt-graphite` skill for Graphite concepts and mental model
- For executing gt CLI commands directly, use devrun agent (see devrun kit)
