# erk-dev - Development CLI

A general-purpose CLI for development tools and scripts used during erk development.

## Architecture

For detailed architecture documentation, see [docs/WORKSTACK_DEV.md](../../../docs/WORKSTACK_DEV.md).

## Quick Start

```bash
# View available commands
erk-dev --help

# Example commands
erk-dev clean-cache --dry-run
erk-dev publish-to-pypi
```

## Shell Completions

`erk-dev` supports tab completion for bash, zsh, and fish shells.

### Quick Setup

**Bash:**

```bash
echo 'source <(erk-dev completion bash)' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**

```bash
echo 'source <(erk-dev completion zsh)' >> ~/.zshrc
source ~/.zshrc
```

**Fish:**

```fish
mkdir -p ~/.config/fish/completions
erk-dev completion fish > ~/.config/fish/completions/erk-dev.fish
```

### Temporary Installation (Current Session Only)

Test completions without permanent installation:

**Bash/Zsh:**

```bash
source <(erk-dev completion [bash|zsh])
```

**Fish:**

```fish
erk-dev completion fish | source
```

### Verification

After setup, test completions:

```bash
erk-dev <TAB>  # Should show: clean-cache, completion, create-agents-symlinks, publish-to-pypi
```
