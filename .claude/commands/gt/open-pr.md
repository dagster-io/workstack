---
description: Open current branch's PR in Graphite web interface
---

# Open PR in Graphite

Opens the current branch's pull request in the Graphite web interface using your default browser.

## What This Command Does

1. **Get current branch's PR**: Uses `gh pr view` to check if current branch has an associated PR
2. **Get repository info**: Extracts owner and repo name from GitHub
3. **Open in browser**: Opens the Graphite PR URL in your default browser

## Usage

```bash
/gt:open-pr
```

## Implementation

When this command is invoked:

### 1. Get Repository Information

```bash
gh repo view --json nameWithOwner
```

Parse the JSON output to extract `owner` and `repo` from `nameWithOwner` (format: "owner/repo").

**Error handling**: If command fails or output is invalid, show error message and exit.

### 2. Get PR Number for Current Branch

```bash
gh pr view --json number
```

Parse the JSON output to extract the `number` field.

**Error handling**: If command fails (no PR exists for current branch), show friendly message:

```
No pull request found for current branch. Create one with:
  /gt:submit-branch
```

### 3. Construct Graphite URL and Open

Format the Graphite PR URL:

```
https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}/
```

Open the URL in default browser:

```bash
open "https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}/"
```

**Success message**: After opening, confirm with:

```
✓ Opened PR #{pr_number} in Graphite
```

## Example Output

### Success Case

```
✓ Opened PR #235 in Graphite
```

### No PR Case

```
No pull request found for current branch. Create one with:
  /gt:submit-branch
```

## Notes

- Uses `gh` CLI to get PR information (requires GitHub CLI to be installed and authenticated)
- Opens in default browser via `open` command (macOS)
- Graphite URL format: `https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}/`
