# Migrating Anthropic Skills to dot-agent

## Overview

Convert standalone Anthropic skills to leverage dot-agent's CLI commands, hooks, and kit system for better integration and discoverability.

## Migration Process

### Step 1: Analyze Existing Skill

Review the Anthropic skill structure:

```
anthropic-skill/
├── SKILL.md
├── scripts/           # Python/bash scripts
├── references/        # Documentation
└── assets/           # Templates, resources
```

Identify:

- Scripts that should become CLI commands
- File patterns for automatic triggering
- Reference documentation to keep
- Assets that are still needed

### Step 2: Create Kit Structure

```bash
# Create new kit
mkdir my-kit
cd my-kit

# Initialize structure
mkdir -p skills/my-skill/references
mkdir -p src/my_kit
mkdir tests

# Move skill content
cp -r /path/to/anthropic-skill/SKILL.md skills/my-skill/
cp -r /path/to/anthropic-skill/references/* skills/my-skill/references/
```

### Step 3: Convert Scripts to CLI Commands

#### Before (Anthropic Script)

```python
# scripts/process_data.py
#!/usr/bin/env python3
import sys
import json

def process_file(filename):
    with open(filename) as f:
        data = json.load(f)
    # Process data
    print(json.dumps(data))

if __name__ == '__main__':
    process_file(sys.argv[1])
```

#### After (dot-agent CLI Command)

```python
# src/my_kit/commands.py
import click
import json
from pathlib import Path

@click.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path())
@click.option('--format', type=click.Choice(['json', 'yaml']))
def process_data(filename: str, output: str | None, format: str):
    """Process data file with enhanced options."""
    data = json.loads(Path(filename).read_text())

    # Process data with better error handling
    try:
        processed = transform_data(data)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Output with format support
    if format == 'yaml':
        import yaml
        result = yaml.dump(processed)
    else:
        result = json.dumps(processed, indent=2)

    if output:
        Path(output).write_text(result)
        click.echo(f"✅ Saved to {output}")
    else:
        click.echo(result)
```

Register in kit.toml:

```toml
[commands.process-data]
type = "python"
module = "my_kit.commands"
function = "process_data"
description = "Process data files with format conversion"
```

### Step 4: Add Hooks for Discovery

Create activation hooks:

```python
# src/my_kit/hooks.py
import click
import os
import sys

@click.command()
def skill_reminder():
    """Remind to load skill for relevant files."""
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')

    # Check if skill applies
    if matches_skill_patterns(file_pattern):
        click.echo(
            "🔴 Load my-skill for data processing",
            err=True
        )

    sys.exit(0)

def matches_skill_patterns(pattern: str) -> bool:
    """Check if file matches skill patterns."""
    extensions = {'.json', '.yaml', '.csv'}
    return any(pattern.endswith(ext) for ext in extensions)
```

### Step 5: Update SKILL.md

#### Before (Anthropic Style)

````markdown
## Scripts

### process_data.py

Process JSON data files:

```bash
python scripts/process_data.py input.json > output.json
```
````

````

#### After (dot-agent Style)

```markdown
## CLI Commands

### Data Processing

Process files with format conversion:

```bash
# Basic processing
dot-agent run my-kit process-data input.json

# With output file
dot-agent run my-kit process-data input.json -o output.yaml

# With format conversion
dot-agent run my-kit process-data input.json --format yaml
````

Available commands:

- **process-data** - Transform and convert data files
- **validate-schema** - Validate against JSON schema
- **generate-sample** - Create sample data files

## Activation

This skill activates automatically when editing:

- JSON files (`*.json`)
- YAML files (`*.yaml`, `*.yml`)
- CSV files (`*.csv`)

Manual activation:

- Load skill `my-skill`

```

## Migration Examples

### Example 1: PDF Processing Skill

**Anthropic Structure:**
```

pdf-skill/
├── SKILL.md
├── scripts/
│ ├── merge_pdfs.py
│ ├── split_pdf.py
│ └── extract_text.py
└── references/
└── pdf_operations.md

```

**dot-agent Kit Structure:**
```

pdf-kit/
├── kit.toml
├── pyproject.toml
├── skills/
│ └── pdf-processor/
│ ├── SKILL.md
│ └── references/
│ └── pdf_operations.md
└── src/
└── pdf_kit/
├── commands.py # All PDF operations
└── hooks.py # PDF file detection

````

**Benefits:**
- Commands discoverable via `dot-agent run pdf-kit`
- Can use external libraries (PyPDF2, pdfplumber)
- Testable with pytest
- Auto-activates for PDF files

### Example 2: API Testing Skill

**Anthropic Approach:**
```python
# scripts/test_api.py
#!/usr/bin/env python3
import requests
import sys

response = requests.get(sys.argv[1])
print(response.json())
````

**dot-agent Approach:**

```python
# src/api_kit/commands.py
@click.command()
@click.argument('endpoint')
@click.option('--method', default='GET')
@click.option('--data', type=click.File('r'))
@click.option('--headers', multiple=True)
@click.option('--auth', envvar='API_KEY')
def test_api(endpoint, method, data, headers, auth):
    """Comprehensive API testing tool."""
    # Build headers
    header_dict = dict(h.split(':', 1) for h in headers)
    if auth:
        header_dict['Authorization'] = f'Bearer {auth}'

    # Make request with error handling
    try:
        response = make_request(method, endpoint, data, header_dict)
        display_response(response)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
```

## Common Migration Patterns

### Pattern 1: Script Collection → Command Group

**Before:**
Multiple script files

**After:**

```python
@click.group()
def data():
    """Data processing commands."""
    pass

@data.command()
def validate():
    """Validate data."""
    pass

@data.command()
def transform():
    """Transform data."""
    pass

# Usage: dot-agent run my-kit data validate
```

### Pattern 2: Bundled Templates → External Resources

**Before:**
Templates in assets/ directory

**After:**
Templates in package resources or downloaded on-demand:

```python
from importlib import resources

@click.command()
def generate_from_template(template_name):
    """Generate from template."""
    # Load from package
    template = resources.read_text('my_kit.templates', f'{template_name}.tpl')
    # Or download if needed
    if not template:
        template = download_template(template_name)
```

### Pattern 3: Environment Scripts → Configuration

**Before:**

```bash
# scripts/setup_env.sh
export API_KEY=xxx
export DB_URL=yyy
```

**After:**

```python
@click.command()
@click.option('--config', type=click.Path(), envvar='MY_KIT_CONFIG')
def configure(config):
    """Load configuration from file or environment."""
    if config:
        load_dotenv(config)
    # Commands automatically use environment variables
```

## Migration Checklist

- [ ] Create kit directory structure
- [ ] Convert scripts to CLI commands
- [ ] Add commands to kit.toml
- [ ] Create hook for automatic activation
- [ ] Update SKILL.md with new command syntax
- [ ] Move references to skill directory
- [ ] Add tests for commands
- [ ] Configure pyproject.toml dependencies
- [ ] Test via `dot-agent run`
- [ ] Update documentation

## Benefits After Migration

| Aspect           | Anthropic Skill  | dot-agent Kit             |
| ---------------- | ---------------- | ------------------------- |
| **Discovery**    | Manual loading   | Auto-activation via hooks |
| **Commands**     | Script execution | CLI with help text        |
| **Dependencies** | Manual install   | pip/pyproject.toml        |
| **Testing**      | Difficult        | Standard pytest           |
| **Distribution** | Zip file         | Git/PyPI                  |
| **Versioning**   | In skill only    | Semantic versioning       |
| **Integration**  | Standalone       | Part of ecosystem         |

## Gradual Migration

You don't need to migrate everything at once:

### Phase 1: Wrapper Kit

Create a minimal kit that wraps existing scripts:

```python
@click.command()
@click.argument('script_name')
@click.argument('args', nargs=-1)
def run_legacy_script(script_name, args):
    """Run legacy Anthropic script."""
    script_path = Path(__file__).parent / 'legacy_scripts' / f'{script_name}.py'
    subprocess.run(['python', script_path] + list(args))
```

### Phase 2: Convert Critical Scripts

Migrate the most-used scripts to proper commands

### Phase 3: Add Enhancements

Add features that weren't possible before:

- Progress bars
- Better error handling
- Format conversion
- Parallel processing

### Phase 4: Full Migration

Complete the migration with hooks and tests

## Maintaining Compatibility

Keep backward compatibility during migration:

```python
@click.command()
@click.argument('input_file')
@click.option('--legacy', is_flag=True, hidden=True)
def process(input_file, legacy):
    """Process file (supports legacy mode)."""
    if legacy:
        # Old behavior for compatibility
        legacy_process(input_file)
    else:
        # New enhanced behavior
        enhanced_process(input_file)
```
