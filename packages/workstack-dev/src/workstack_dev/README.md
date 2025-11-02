# workstack-dev - Development CLI

A general-purpose CLI for development tools and scripts used during workstack development.

## Architecture

For detailed architecture documentation, see [docs/WORKSTACK_DEV.md](../../../docs/WORKSTACK_DEV.md).

## Quick Start

```bash
# View available commands
workstack-dev --help

# Example commands
workstack-dev clean-cache --dry-run
workstack-dev publish-to-pypi
```

## Shell Completions

`workstack-dev` supports tab completion for bash, zsh, and fish shells.

### Quick Setup

**Bash:**

```bash
echo 'source <(workstack-dev completion bash)' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**

```bash
echo 'source <(workstack-dev completion zsh)' >> ~/.zshrc
source ~/.zshrc
```

**Fish:**

```fish
mkdir -p ~/.config/fish/completions
workstack-dev completion fish > ~/.config/fish/completions/workstack-dev.fish
```

### Temporary Installation (Current Session Only)

Test completions without permanent installation:

**Bash/Zsh:**

```bash
source <(workstack-dev completion [bash|zsh])
```

**Fish:**

```fish
workstack-dev completion fish | source
```

### Verification

After setup, test completions:

```bash
workstack-dev <TAB>  # Should show: clean-cache, completion, create-agents-symlinks, publish-to-pypi
```
