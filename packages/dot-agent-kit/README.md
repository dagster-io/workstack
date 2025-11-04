# dot-agent-kit

Kit management system for Claude Code.

## Package vs CLI

- **Package name**: `dot-agent-kit` (what you install)
- **CLI command**: `dot-agent` (what you run)

This naming follows the convention where the package name describes what it provides (a kit management system), while the CLI command is concise for frequent use.

## Installation

```bash
uv pip install dot-agent-kit
```

Or with pip:

```bash
pip install dot-agent-kit
```

## Usage

After installation, use the `dot-agent` command:

```bash
# Initialize configuration
dot-agent init

# View available commands
dot-agent --help

# Manage kits
dot-agent kit install <kit-name>
dot-agent kit list
```

## Creating Kits

### Kit Structure

A kit is a collection of Claude Code artifacts (agents, skills, commands) distributed as a package. Each kit requires:

1. **kit.yaml** - Manifest file with kit metadata and artifact paths
2. **Artifacts** - The actual agent, skill, and command files

### Namespace Pattern (Required)

**All bundled kits** must follow the namespace pattern:

```
{artifact_type}s/{kit_name}/...
```

This organizational pattern:

- Prevents naming conflicts when multiple kits are installed
- Makes it clear which kit an artifact belongs to
- Enables clean uninstallation of kit artifacts
- Keeps the `.claude/` directory organized

**Example structure:**

```
my-kit/
├── kit.yaml
├── agents/
│   └── my-kit/
│       └── my-agent.md
└── skills/
    └── my-kit/
        ├── tool-a/
        │   └── SKILL.md
        └── tool-b/
            └── SKILL.md
```

**Example kit.yaml:**

```yaml
name: my-kit
version: 1.0.0
description: My awesome Claude Code kit
artifacts:
  agent:
    - agents/my-kit/my-agent.md
  skill:
    - skills/my-kit/tool-a/SKILL.md
    - skills/my-kit/tool-b/SKILL.md
```

### Invocation Names vs File Paths

**Important**: Claude Code discovers artifacts by their filename/directory name, not the full path:

- **Agents**: Discovered by filename (e.g., `agents/my-kit/helper.md` → invoked as "helper")
- **Skills**: Discovered by directory name (e.g., `skills/my-kit/pytest/SKILL.md` → invoked as "pytest")
- **Commands**: Discovered by filename (e.g., `commands/my-kit/build.md` → invoked as "/build")

The namespace directory (`my-kit/`) is **organizational only** - it doesn't become part of the invocation name.

**Hyphenated naming convention (kebab-case)**: ALL artifacts MUST use hyphenated naming (kebab-case), NOT underscores. Use hyphens to combine words (e.g., `skills/devrun-make/SKILL.md` → "devrun-make", `commands/my-command.md` → "/my-command"). This is the standard for ALL Claude artifacts - bundled kits and project-local alike.

**DO NOT use underscores** (`_`) in artifact names. Use hyphens (`-`) instead:

- ✅ CORRECT: `my-command.md`, `api-client/SKILL.md`, `test-runner.md`
- ❌ WRONG: `my_command.md`, `api_client/SKILL.md`, `test_runner.md`

Exception: Python scripts within artifacts may use snake_case (they're code, not artifacts).

### Namespace Standards for Kit Types

**Bundled kits** (distributed with packages): Should follow hyphenated naming convention (e.g., `skills/kit-name-tool/`) to avoid naming conflicts and maintain clear organization.

**Project-local artifacts** (in `.claude/` not from kits): MUST also use kebab-case naming. The hyphenated naming standard applies to ALL artifacts, regardless of whether they're bundled or project-local.

### Adopting Hyphenated Naming

To align with the standard hyphenated naming convention:

1. **Flatten directory structure with hyphenated names:**

   ```bash
   # Example: Convert skills/devrun/make/ to skills/devrun-make/
   mv skills/devrun/make skills/devrun-make
   mv skills/devrun/pytest skills/devrun-pytest
   ```

2. **Update kit.yaml artifact paths:**

   ```yaml
   artifacts:
     skill:
       - skills/devrun-make/SKILL.md # Was: skills/devrun/make/SKILL.md
       - skills/devrun-pytest/SKILL.md # Was: skills/devrun/pytest/SKILL.md
   ```

3. **Test installation** to verify paths are correct
