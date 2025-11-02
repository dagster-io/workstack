# GitHub CLI (gh) Mental Model

**Last Updated**: 2025-10-13

A comprehensive guide to understanding GitHub CLI's mental model, command structure, and integration patterns.

---

## Table of Contents

- [What is GitHub CLI?](#what-is-github-cli)
- [Core Mental Model](#core-mental-model)
- [Terminology](#terminology)
- [Authentication & Configuration](#authentication--configuration)
- [Command Reference](#command-reference)
- [Workflow Patterns](#workflow-patterns)
- [Workstack Integration](#workstack-integration)
- [Practical Examples](#practical-examples)
- [Key Insights for AI Agents](#key-insights-for-ai-agents)

---

## What is GitHub CLI?

GitHub CLI (`gh`) is the official command-line tool for interacting with GitHub. It brings pull requests, issues, releases, workflows, and other GitHub features directly to your terminal.

### The Problem It Solves

Without GitHub CLI, you need to:

1. Switch to a web browser for every GitHub operation
2. Write complex `curl` commands to interact with the GitHub API
3. Maintain authentication tokens manually
4. Parse JSON responses in shell scripts
5. Navigate multiple web pages to check PR status, CI runs, etc.

With GitHub CLI, you can:

- Create and manage PRs from your terminal
- View and update issues without leaving your workflow
- Monitor CI/CD runs in real-time
- Clone, fork, and manage repositories instantly
- Script GitHub operations with clean command syntax
- Access the full GitHub API with built-in authentication

### Core Philosophy

**Think in GitHub entities, not web pages.** GitHub CLI provides direct access to GitHub resources (PRs, issues, repos, workflows) as first-class command-line objects.

```
Repository
  ├─ Pull Requests (gh pr ...)
  │    ├─ Reviews
  │    ├─ Comments
  │    └─ CI Checks
  ├─ Issues (gh issue ...)
  │    ├─ Comments
  │    └─ Labels
  ├─ Workflows (gh run ...)
  │    └─ Jobs & Logs
  └─ Releases (gh release ...)
```

Each entity has CRUD operations accessible via `gh` commands, making GitHub operations as natural as git operations.

---

## Core Mental Model

### GitHub Entities vs Git Objects

**Critical distinction**: `gh` operates on GitHub-hosted entities, while `git` operates on local repository objects.

| Entity Type              | Tool  | Scope         | Example                       |
| ------------------------ | ----- | ------------- | ----------------------------- |
| Commits, branches, files | `git` | Local repo    | `git commit`, `git branch`    |
| PRs, issues, CI runs     | `gh`  | GitHub remote | `gh pr create`, `gh run list` |

**Key insight**: `gh` is **stateless** - it queries GitHub's API on every command. Unlike git (which has a local `.git` directory) or Graphite (which has `.graphite_cache_persist`), `gh` maintains no local state beyond authentication credentials.

### Authentication Model

`gh` uses OAuth tokens stored in your system's credential manager:

```
~/.config/gh/
  ├─ hosts.yml           # Authentication tokens per host
  └─ config.yml          # User preferences
```

**Authentication flow**:

1. `gh auth login` - Interactive OAuth flow
2. Token stored securely in system keychain
3. All subsequent commands use stored token
4. Token refreshed automatically when needed

### Repository Context

`gh` automatically detects repository context from:

1. Current directory's git remote (`origin` by default)
2. `GH_REPO` environment variable
3. `-R/--repo` flag for explicit override

```bash
# Implicit context (uses current directory's git remote)
gh pr list

# Explicit context
gh pr list -R owner/repo

# Environment variable
export GH_REPO=owner/repo
gh pr list
```

### API Integration

Every `gh` command is a wrapper around GitHub's REST or GraphQL APIs:

- **REST API**: Most commands use REST endpoints
- **GraphQL API**: Complex queries use GraphQL (`gh api graphql`)
- **JSON output**: All commands support `--json` for programmatic access
- **Rate limits**: Inherits GitHub API rate limits (5000 req/hour for authenticated)

### Output Modes

`gh` provides multiple output formats:

| Mode           | Flag                       | Use Case           |
| -------------- | -------------------------- | ------------------ |
| Human-readable | (default)                  | Terminal viewing   |
| JSON           | `--json <fields>`          | Scripting, parsing |
| Template       | `--template <go-template>` | Custom formatting  |
| Web            | `--web`                    | Open in browser    |

---

## Terminology

### Essential Terms

| Term        | Definition                                    | Example                    |
| ----------- | --------------------------------------------- | -------------------------- |
| **PR**      | Pull Request - proposed changes to repository | `gh pr create`             |
| **Issue**   | Task, bug, or feature request                 | `gh issue create`          |
| **Run**     | Workflow execution (CI/CD job)                | `gh run view 123`          |
| **Release** | Tagged version with assets                    | `gh release create v1.0.0` |
| **Gist**    | Code snippet or paste                         | `gh gist create file.txt`  |
| **Repo**    | Repository (codebase)                         | `gh repo view`             |
| **Fork**    | Personal copy of someone else's repo          | `gh repo fork`             |
| **Head**    | Source branch of a PR                         | `--head my-branch`         |
| **Base**    | Target branch of a PR                         | `--base main`              |
| **Draft**   | PR not ready for review                       | `gh pr create --draft`     |
| **Checks**  | CI/CD status for a PR                         | PR checks (pass/fail)      |

### PR States

| State    | Meaning                       | Transitions          |
| -------- | ----------------------------- | -------------------- |
| `OPEN`   | Active, awaiting review/merge | → `MERGED`, `CLOSED` |
| `MERGED` | Accepted and merged           | (terminal)           |
| `CLOSED` | Rejected or abandoned         | → `OPEN` (reopen)    |
| `DRAFT`  | Work in progress, not ready   | → `OPEN` (ready)     |

### Check States

| State     | Meaning                       | Example                      |
| --------- | ----------------------------- | ---------------------------- |
| `SUCCESS` | All checks passed             | CI tests passed              |
| `FAILURE` | One or more checks failed     | Linting errors               |
| `PENDING` | Checks in progress            | Tests running                |
| `SKIPPED` | Check skipped                 | Not required for this branch |
| `NEUTRAL` | Check completed, no pass/fail | Informational check          |

---

## Authentication & Configuration

### Initial Setup

#### `gh auth login`

Authenticate with GitHub.

```bash
gh auth login                     # Interactive OAuth flow
```

**Interactive prompts**:

1. GitHub.com or GitHub Enterprise?
2. HTTPS or SSH protocol?
3. Authenticate via web browser or token?
4. Web: Opens browser → authorize app → done
5. Token: Paste personal access token

**What it does**:

- Stores OAuth token in system keychain
- Configures git protocol (HTTPS/SSH)
- Sets up git credential helper
- Creates `~/.config/gh/hosts.yml`

#### `gh auth status`

Check authentication state.

```bash
gh auth status                    # Show current authentication

# Output:
# github.com
#   ✓ Logged in to github.com as schrockn (oauth_token)
#   ✓ Git operations configured to use https protocol
#   ✓ Token: gho_***
#   ✓ Token scopes: gist, read:org, repo, workflow
```

#### `gh auth token`

Print authentication token (for scripting).

```bash
gh auth token                     # Print token
export GH_TOKEN=$(gh auth token)  # Use in scripts
```

### Configuration

#### `gh config set <key> <value>`

Set configuration options.

```bash
gh config set editor vim          # Set editor for PR bodies
gh config set git_protocol ssh    # Use SSH for git operations
gh config set browser firefox     # Set browser for --web flag
gh config set pager less          # Set pager for long output
```

**Common settings**:

- `editor`: Editor for PR/issue descriptions
- `git_protocol`: https or ssh
- `browser`: Browser for `--web` flag
- `pager`: Pager for command output (less, more, cat)
- `prompt`: Enable/disable interactive prompts

#### `gh repo set-default`

Set default repository for current directory.

```bash
gh repo set-default owner/repo    # Set default repo
```

**What it does**:

- Creates `.git/config` entry for `gh.repo`
- Subsequent `gh` commands use this repo by default
- Overrides git remote detection

---

## Command Reference

### Pull Request Commands

#### `gh pr list`

List pull requests in repository.

```bash
gh pr list                        # List open PRs
gh pr list --state all            # All PRs (open, merged, closed)
gh pr list --state merged         # Only merged PRs
gh pr list --author @me           # Your PRs
gh pr list --assignee schrockn    # PRs assigned to user
gh pr list --label bug            # PRs with "bug" label
gh pr list --search "draft"       # Search PR titles/bodies
gh pr list --limit 50             # Limit results
gh pr list --json number,title    # JSON output with specific fields
```

**JSON output fields**:

```bash
--json number           # PR number
--json title            # PR title
--json state            # OPEN, MERGED, CLOSED
--json headRefName      # Source branch name
--json baseRefName      # Target branch name
--json url              # GitHub URL
--json isDraft          # Draft status
--json statusCheckRollup # CI check statuses
--json reviewDecision   # Review status
--json author           # Author info
--json createdAt        # Creation timestamp
```

**Performance tip**: Fetching `statusCheckRollup` is slower. Only include when needed.

#### `gh pr view`

View pull request details.

```bash
gh pr view 123                    # View PR #123
gh pr view --web                  # Open current branch's PR in browser
gh pr view --json title,body      # JSON output
gh pr view --comments             # Include comments
gh pr view --json statusCheckRollup # Include CI check details
```

**Output**:

```
Add feature X #123
Draft • schrockn wants to merge 3 commits into main from feature-x

  This PR adds feature X to improve performance.

  - Adds new API endpoint
  - Updates documentation

View this pull request on GitHub: https://github.com/owner/repo/pull/123
```

#### `gh pr create`

Create a new pull request.

```bash
gh pr create                      # Interactive prompts
gh pr create --title "Fix bug"    # Set title
gh pr create --body "Details"     # Set description
gh pr create --draft              # Create as draft
gh pr create --base main          # Set target branch
gh pr create --head feature       # Set source branch
gh pr create --fill               # Use commit messages for title/body
gh pr create --web                # Open browser to create PR
gh pr create --reviewer user1     # Request reviews
gh pr create --assignee @me       # Assign yourself
gh pr create --label bug          # Add labels
```

**Interactive flow**:

1. Detects current branch vs default branch
2. Prompts for title (defaults to last commit message)
3. Prompts for body (opens editor)
4. Shows preview
5. Confirms creation
6. Prints PR URL

**Options**:

- `--draft`: Create as draft PR
- `--fill`: Auto-fill from commit messages
- `--web`: Open browser instead of CLI
- `--title/-t`: PR title
- `--body/-b`: PR description
- `--base/-B`: Target branch (default: default branch)
- `--head/-H`: Source branch (default: current)
- `--reviewer/-r`: Request reviews
- `--assignee/-a`: Assign users
- `--label/-l`: Add labels
- `--milestone/-m`: Set milestone
- `--project/-p`: Add to project

#### `gh pr checkout`

Check out a pull request locally.

```bash
gh pr checkout 123                # Checkout PR #123
gh pr checkout feature-branch     # Checkout by branch name
gh pr checkout https://...        # Checkout by URL
```

**What it does**:

1. Fetches PR branch from remote
2. Creates local branch tracking remote
3. Checks out the branch
4. Ready to test changes locally

**Alias**: `gh co 123` (if alias configured)

#### `gh pr status`

Show status of relevant PRs.

```bash
gh pr status                      # Show PR status for current user

# Output:
# Current branch
#   #123  Add feature X [user1]
#
# Created by you
#   #124  Fix bug Y [Checks passing]
#   #125  Update docs [Draft]
#
# Requesting a code review from you
#   #126  Refactor Z [user2]
```

#### `gh pr checks`

View CI check status for a PR.

```bash
gh pr checks                      # Show checks for current branch
gh pr checks 123                  # Show checks for PR #123
gh pr checks --watch              # Watch checks in real-time
```

**Output**:

```
All checks have passed
✓ test     Tests   1m23s  https://...
✓ lint     Lint    45s    https://...
✓ build    Build   2m10s  https://...
```

#### `gh pr merge`

Merge a pull request.

```bash
gh pr merge 123                   # Interactive merge
gh pr merge --merge               # Create merge commit
gh pr merge --squash              # Squash and merge
gh pr merge --rebase              # Rebase and merge
gh pr merge --auto                # Enable auto-merge
gh pr merge --delete-branch       # Delete branch after merge
```

**Options**:

- `--merge`: Create merge commit (default)
- `--squash`: Squash commits into one
- `--rebase`: Rebase onto base branch
- `--auto`: Enable auto-merge when checks pass
- `--delete-branch`: Delete head branch after merge
- `--subject`: Custom merge commit message
- `--body`: Custom merge commit body

#### `gh pr close`

Close a pull request.

```bash
gh pr close 123                   # Close PR
gh pr close --comment "Reason"    # Close with comment
gh pr close --delete-branch       # Delete branch too
```

#### `gh pr reopen`

Reopen a closed pull request.

```bash
gh pr reopen 123                  # Reopen PR
```

#### `gh pr ready`

Mark draft PR as ready for review.

```bash
gh pr ready 123                   # Mark as ready
gh pr ready                       # Mark current branch's PR
```

#### `gh pr edit`

Edit pull request metadata.

```bash
gh pr edit 123 --title "New title"
gh pr edit 123 --body "New description"
gh pr edit 123 --add-reviewer user1
gh pr edit 123 --add-label bug
gh pr edit 123 --base main        # Change target branch
```

#### `gh pr review`

Add review to a pull request.

```bash
gh pr review 123                  # Interactive review
gh pr review 123 --approve        # Approve PR
gh pr review 123 --request-changes # Request changes
gh pr review 123 --comment        # Comment only
gh pr review 123 --body "LGTM"    # Review comment
```

#### `gh pr diff`

View PR changes.

```bash
gh pr diff 123                    # View diff for PR #123
gh pr diff                        # Diff for current branch's PR
gh pr diff --patch                # Use patch format
```

#### `gh pr comment`

Add comment to PR.

```bash
gh pr comment 123 --body "Comment"
gh pr comment 123 --body-file comment.txt
```

---

### Issue Commands

#### `gh issue list`

List issues in repository.

```bash
gh issue list                     # List open issues
gh issue list --state all         # All issues
gh issue list --state closed      # Closed issues
gh issue list --author @me        # Your issues
gh issue list --assignee schrockn # Assigned to user
gh issue list --label bug         # Issues with label
gh issue list --search "error"    # Search issues
gh issue list --limit 50          # Limit results
gh issue list --json number,title # JSON output
```

#### `gh issue view`

View issue details.

```bash
gh issue view 123                 # View issue #123
gh issue view --web               # Open in browser
gh issue view --comments          # Include comments
gh issue view --json title,body   # JSON output
```

#### `gh issue create`

Create a new issue.

```bash
gh issue create                   # Interactive
gh issue create --title "Bug X"   # Set title
gh issue create --body "Details"  # Set body
gh issue create --label bug       # Add label
gh issue create --assignee @me    # Assign yourself
gh issue create --web             # Open browser
```

#### `gh issue close`

Close an issue.

```bash
gh issue close 123                # Close issue
gh issue close 123 --comment "Reason"
```

#### `gh issue reopen`

Reopen a closed issue.

```bash
gh issue reopen 123
```

#### `gh issue edit`

Edit issue metadata.

```bash
gh issue edit 123 --title "New title"
gh issue edit 123 --body "New body"
gh issue edit 123 --add-label bug
gh issue edit 123 --add-assignee user1
```

#### `gh issue comment`

Add comment to issue.

```bash
gh issue comment 123 --body "Comment"
```

---

### Repository Commands

#### `gh repo view`

View repository details.

```bash
gh repo view                      # Current repo
gh repo view owner/repo           # Specific repo
gh repo view --web                # Open in browser
gh repo view --json name,description
```

#### `gh repo clone`

Clone repository.

```bash
gh repo clone owner/repo          # Clone repo
gh repo clone owner/repo mydir    # Clone to directory
```

**Advantages over `git clone`**:

- Handles authentication automatically
- Supports `owner/repo` shorthand
- Configures remotes appropriately for forks

#### `gh repo fork`

Fork a repository.

```bash
gh repo fork                      # Fork current repo
gh repo fork owner/repo           # Fork specific repo
gh repo fork --clone              # Fork and clone locally
gh repo fork --remote             # Add fork as remote
```

#### `gh repo create`

Create new repository.

```bash
gh repo create                    # Interactive
gh repo create my-repo            # Create repo
gh repo create my-repo --public   # Public repo
gh repo create my-repo --private  # Private repo
gh repo create my-repo --clone    # Create and clone
```

#### `gh repo list`

List repositories.

```bash
gh repo list                      # Your repos
gh repo list owner                # User/org repos
gh repo list --limit 50           # Limit results
gh repo list --json name,url      # JSON output
```

---

### Workflow Commands

#### `gh run list`

List workflow runs.

```bash
gh run list                       # Recent runs
gh run list --workflow ci.yml     # Specific workflow
gh run list --branch main         # Runs on branch
gh run list --event push          # Runs triggered by event
gh run list --json status,conclusion
```

#### `gh run view`

View workflow run details.

```bash
gh run view 123456                # View run
gh run view --log                 # Show logs
gh run view --job 789             # View specific job
gh run view --web                 # Open in browser
```

#### `gh run watch`

Watch a workflow run in real-time.

```bash
gh run watch 123456               # Watch run
gh run watch                      # Watch latest run
```

**Output**: Live updates as jobs complete.

#### `gh run rerun`

Rerun a workflow.

```bash
gh run rerun 123456               # Rerun workflow
gh run rerun 123456 --failed      # Rerun only failed jobs
```

---

### Release Commands

#### `gh release list`

List releases.

```bash
gh release list                   # All releases
gh release list --limit 10        # Limit results
gh release list --json tagName,name
```

#### `gh release view`

View release details.

```bash
gh release view v1.0.0            # View release
gh release view --web             # Open in browser
gh release view --json assets     # JSON output
```

#### `gh release create`

Create a new release.

```bash
gh release create v1.0.0          # Interactive
gh release create v1.0.0 --title "Release 1.0"
gh release create v1.0.0 --notes "Changes..."
gh release create v1.0.0 dist/*   # Upload assets
gh release create v1.0.0 --draft  # Create draft
gh release create v1.0.0 --prerelease
```

#### `gh release upload`

Upload assets to release.

```bash
gh release upload v1.0.0 file.zip
gh release upload v1.0.0 dist/*   # Upload multiple
```

#### `gh release download`

Download release assets.

```bash
gh release download v1.0.0        # Download all assets
gh release download v1.0.0 --pattern "*.zip"
```

---

### API Commands

#### `gh api`

Make authenticated GitHub API requests.

```bash
# REST API
gh api repos/{owner}/{repo}/issues
gh api repos/{owner}/{repo}/pulls/123
gh api -X POST repos/{owner}/{repo}/issues \
  -f title="Bug" -f body="Details"

# GraphQL
gh api graphql -f query='
  query {
    viewer {
      login
      repositories(first: 5) {
        nodes { name }
      }
    }
  }
'

# Pagination
gh api --paginate repos/{owner}/{repo}/issues

# JQ filtering
gh api repos/{owner}/{repo}/issues --jq '.[].title'

# Headers
gh api -H "Accept: application/vnd.github.v3+json" ...
```

**Placeholders**:

- `{owner}`: Repository owner (auto-detected)
- `{repo}`: Repository name (auto-detected)
- `{branch}`: Current branch (auto-detected)

**Options**:

- `-X/--method`: HTTP method (GET, POST, PATCH, DELETE)
- `-f/--raw-field`: String parameter
- `-F/--field`: Typed parameter (JSON types)
- `--paginate`: Fetch all pages
- `--jq`: Filter with jq
- `-H/--header`: Custom header
- `--cache`: Cache response

---

### Additional Commands

#### `gh browse`

Open repository in browser.

```bash
gh browse                         # Open repo home
gh browse issues                  # Open issues page
gh browse pulls                   # Open PRs page
gh browse wiki                    # Open wiki
```

#### `gh search`

Search GitHub.

```bash
gh search repos "workstack"       # Search repos
gh search issues "bug" --repo owner/repo
gh search prs "feature"           # Search PRs
gh search code "function"         # Search code
```

#### `gh alias`

Manage command aliases.

```bash
gh alias set co "pr checkout"     # gh co 123
gh alias set pv "pr view --web"   # gh pv
gh alias list                     # List aliases
```

---

## Workflow Patterns

### Pattern 1: Creating and Merging a PR

**Goal**: Complete feature development workflow from branch to merge.

```bash
# 1. Create feature branch (git)
git checkout -b feature-x
# ... make changes ...
git add .
git commit -m "Add feature X"
git push -u origin feature-x

# 2. Create PR (gh)
gh pr create --title "Add feature X" --body "Implements feature X for better performance" --draft

# 3. Mark ready when done
gh pr ready

# 4. Request reviews
gh pr edit --add-reviewer teammate1,teammate2

# 5. Monitor checks
gh pr checks --watch

# 6. View reviews
gh pr view

# 7. Address feedback
# ... make changes ...
git add .
git commit -m "Address review feedback"
git push

# 8. Merge when approved
gh pr merge --squash --delete-branch
```

### Pattern 2: Reviewing PRs from Terminal

**Goal**: Review PRs without leaving terminal.

```bash
# 1. List PRs needing review
gh pr list --search "review-requested:@me"

# 2. Checkout PR locally
gh pr checkout 123

# 3. View changes
gh pr diff

# 4. Run tests locally
make test

# 5. View full PR details
gh pr view --comments

# 6. Add review
gh pr review --approve --body "LGTM! Tests pass locally."

# Or request changes
gh pr review --request-changes --body "Please address the null check in line 45."

# 7. Return to your branch
git checkout -
```

### Pattern 3: Monitoring CI/CD

**Goal**: Watch workflow runs and debug failures.

```bash
# 1. List recent workflow runs
gh run list --limit 10

# 2. Watch latest run in real-time
gh run watch

# 3. View specific run details
gh run view 123456

# 4. View logs for debugging
gh run view 123456 --log

# 5. Download logs for detailed analysis
gh run view 123456 --log > build.log

# 6. Rerun failed jobs
gh run rerun 123456 --failed

# 7. Check PR checks status
gh pr checks 123 --watch
```

### Pattern 4: Issue-Driven Development

**Goal**: Link issues to PRs and branches.

```bash
# 1. Create issue
gh issue create --title "Fix null pointer bug" --label bug

# Output: Created issue #42

# 2. Create branch referencing issue
git checkout -b fix-issue-42

# 3. Make changes
# ... fix bug ...
git add .
git commit -m "Fix null pointer bug (closes #42)"
git push -u origin fix-issue-42

# 4. Create PR that closes issue
gh pr create --title "Fix null pointer bug" --body "Closes #42"

# 5. When PR merges, issue auto-closes
gh pr merge --squash
```

### Pattern 5: Working Across Multiple Repos

**Goal**: Manage PRs across multiple repositories.

```bash
# 1. List your PRs across all repos
gh search prs --author @me --state open

# 2. Check specific repo without cd
gh pr list -R owner/repo1
gh pr list -R owner/repo2

# 3. Create PR in different repo
gh pr create -R owner/other-repo \
  --title "Update dependency" \
  --base main \
  --head update-deps

# 4. Clone related repo
gh repo clone owner/related-repo

# 5. Check status across repos
for repo in repo1 repo2 repo3; do
  echo "=== $repo ==="
  gh pr list -R owner/$repo
done
```

### Pattern 6: Release Automation

**Goal**: Create and publish releases with assets.

```bash
# 1. Tag version
git tag v1.0.0
git push origin v1.0.0

# 2. Build release artifacts
make build  # Creates dist/

# 3. Create release with assets
gh release create v1.0.0 \
  --title "Release 1.0.0" \
  --notes "$(cat CHANGELOG.md)" \
  dist/*

# 4. Or create draft first
gh release create v1.0.0 --draft \
  --title "Release 1.0.0" \
  dist/*

# 5. Upload additional assets
gh release upload v1.0.0 docs.pdf

# 6. Publish when ready
gh release edit v1.0.0 --draft=false

# 7. View release
gh release view v1.0.0 --web
```

### Pattern 7: Scripting with JSON Output

**Goal**: Build automation scripts using gh JSON output.

```bash
#!/bin/bash
# check-pr-status.sh - Check if PR is ready to merge

PR_NUMBER=$1

# Fetch PR data as JSON
PR_JSON=$(gh pr view "$PR_NUMBER" --json state,isDraft,reviewDecision,statusCheckRollup)

# Extract fields
STATE=$(echo "$PR_JSON" | jq -r '.state')
IS_DRAFT=$(echo "$PR_JSON" | jq -r '.isDraft')
REVIEWS=$(echo "$PR_JSON" | jq -r '.reviewDecision')
CHECKS=$(echo "$PR_JSON" | jq '.statusCheckRollup[] | select(.conclusion != "SUCCESS")')

# Check conditions
if [ "$STATE" != "OPEN" ]; then
  echo "PR is not open"
  exit 1
fi

if [ "$IS_DRAFT" = "true" ]; then
  echo "PR is still draft"
  exit 1
fi

if [ "$REVIEWS" != "APPROVED" ]; then
  echo "PR not approved: $REVIEWS"
  exit 1
fi

if [ -n "$CHECKS" ]; then
  echo "Checks failing:"
  echo "$CHECKS" | jq -r '.name'
  exit 1
fi

echo "PR #$PR_NUMBER is ready to merge!"
gh pr merge "$PR_NUMBER" --squash --delete-branch
```

---

## Workstack Integration

### How Workstack Uses gh

Workstack integrates with GitHub CLI to provide PR information in the worktree list:

#### 1. PR Information Fetching

**File**: `src/workstack/core/github_ops.py`

```python
def get_prs_for_repo(
    self, repo_root: Path, *, include_checks: bool
) -> dict[str, PullRequestInfo]:
    """Get PR information for all branches in the repository."""
```

**What it does**:

- Executes: `gh pr list --state all --json number,headRefName,url,state,isDraft[,statusCheckRollup]`
- Parses JSON output
- Maps `headRefName` (branch) to `PullRequestInfo`
- Returns: `{"feature-branch": PullRequestInfo(...)}`

**Performance consideration**:

- `statusCheckRollup` is **slow** (fetches CI status for each PR)
- Only fetched when `include_checks=True`
- Workstack uses Graphite cache first, falls back to gh

**Usage in workstack**:

```bash
# Shows PR info for each worktree
workstack list

# Output includes:
# feature-branch [PR #123] OPEN ✓ Checks passing
```

#### 2. PR Status Collector

**File**: `src/workstack/status/collectors/github.py`

```python
class GitHubPRCollector(StatusCollector):
    """Collects GitHub pull request information."""
```

**Data flow**:

1. Tries Graphite cache first (fast, but no CI status)
2. Falls back to `gh pr list` if Graphite unavailable
3. Parses PR state, checks, draft status
4. Determines "ready to merge" status

**Ready to merge logic**:

```python
ready_to_merge = (
    pr.state == "OPEN"
    and not pr.is_draft
    and (pr.checks_passing is True or pr.checks_passing is None)
)
```

#### 3. Authentication Handling

**Error boundary pattern**:

```python
try:
    result = subprocess.run(["gh", "pr", "list", ...], check=True)
    # ... parse result ...
except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
    # gh not installed, not authenticated, or JSON parsing failed
    return {}
```

**Why try/except is acceptable here**:

- Cannot reliably check gh installation/auth without duplicating gh's logic
- This is an error boundary (boundary between system and external tool)
- Graceful degradation: workstack continues without PR info

#### 4. Integration with Graphite

**Workstack prefers Graphite cache over gh for performance**:

```python
# Try Graphite first (fast - no CI status)
prs = ctx.graphite_ops.get_prs_from_graphite(ctx.git_ops, repo_root)

# If Graphite data not available, fall back to GitHub
if not prs:
    prs = ctx.github_ops.get_prs_for_repo(repo_root, include_checks=True)
```

**Why**:

- Graphite cache (`.git/.graphite_pr_info`) is local and instant
- `gh pr list` requires API calls (slower, rate-limited)
- Graphite updates cache during `gt sync`

**Trade-off**:

- Graphite cache may be stale between syncs
- gh always fetches latest (but slower)

#### 5. JSON Field Selection

**Workstack uses specific JSON fields for efficiency**:

```python
json_fields = "number,headRefName,url,state,isDraft"
if include_checks:
    json_fields += ",statusCheckRollup"
```

**Available fields** (from gh):

- `number`: PR number
- `title`: PR title
- `body`: PR description
- `state`: OPEN, MERGED, CLOSED
- `isDraft`: Draft status
- `headRefName`: Source branch
- `baseRefName`: Target branch
- `url`: GitHub PR URL
- `statusCheckRollup`: CI check statuses (slow!)
- `reviewDecision`: APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED
- `author`: Author information
- `createdAt`: Creation timestamp

**Field selection strategy**:

- Always fetch: core metadata (number, state, branch, url)
- Conditionally fetch: expensive fields (statusCheckRollup)
- Never fetch unused: title, body, author (reduces response size)

#### 6. URL Parsing

**Workstack extracts owner/repo from PR URLs**:

```python
def _parse_github_pr_url(url: str) -> tuple[str, str] | None:
    """Parse owner and repo from GitHub PR URL."""
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/\d+", url)
    if match:
        return (match.group(1), match.group(2))
    return None
```

**Why**: Needed for operations requiring `owner/repo` context.

### Configuration

**Global config** (`~/.workstack/config.toml`):

```toml
show_pr_info = true     # Enable PR info in listings
```

**When enabled**:

- `workstack list` shows PR status for each worktree
- `workstack status` includes PR information
- Requires `gh` CLI installed and authenticated

**When disabled or gh unavailable**:

- PR info omitted from output
- No errors, graceful degradation
- All other workstack features work normally

### Performance Characteristics

| Operation                  | Method                                | Speed  | Rate Limit |
| -------------------------- | ------------------------------------- | ------ | ---------- |
| List all PRs (no checks)   | `gh pr list`                          | ~500ms | Yes        |
| List all PRs (with checks) | `gh pr list --json statusCheckRollup` | ~2-5s  | Yes        |
| Graphite cache read        | Read `.graphite_pr_info`              | <10ms  | No         |
| Single PR status           | `gh pr view <num>`                    | ~300ms | Yes        |

**Best practices**:

1. Use Graphite cache when available (instant)
2. Fetch checks only when needed (display-time, not listing-time)
3. Batch operations when possible (single `gh pr list` for all branches)
4. Cache results in session when repeated access needed

---

## Practical Examples

### Example 1: Daily Development Workflow

**Scenario**: Working on a feature, creating PR, responding to reviews.

```bash
# Morning: Start new feature
git checkout main
git pull
git checkout -b feature-auth-improvements

# Make changes...
git add .
git commit -m "Add OAuth2 token refresh logic"
git push -u origin feature-auth-improvements

# Create draft PR
gh pr create --draft --fill

# Continue working...
git add .
git commit -m "Add token expiry handling"
git push

# Ready for review
gh pr ready
gh pr edit --add-reviewer teammate1,teammate2 --add-label enhancement

# Check status
gh pr checks --watch

# Review feedback arrives
gh pr view --comments

# Make changes
git add .
git commit -m "Address review comments"
git push

# Approved! Merge it
gh pr merge --squash --delete-branch
git checkout main
git pull
```

### Example 2: Reviewing Multiple PRs

**Scenario**: You're on review duty, need to review several PRs.

```bash
# List PRs needing your review
gh pr list --search "review-requested:@me"

# For each PR:
PR=123

# Quick view
gh pr view $PR

# Detailed review with checkout
gh pr checkout $PR
gh pr diff | less

# Run tests
make test

# Check files changed
git diff main --name-only

# Add review
if tests_pass; then
  gh pr review $PR --approve --body "LGTM! Tested locally."
else
  gh pr review $PR --request-changes --body "Tests failing - see comment."
  gh pr comment $PR --body "The authentication test fails with: ..."
fi

# Next PR
git checkout main
```

### Example 3: Debugging CI Failures

**Scenario**: Your PR's checks are failing, need to diagnose.

```bash
# View check status
gh pr checks 123

# Output shows failure:
# ✓ lint      Lint       45s
# ✗ test      Tests      2m10s  https://...
# ✓ build     Build      1m30s

# View workflow run details
gh run list --branch feature-x
gh run view 789456

# View logs
gh run view 789456 --log | grep ERROR

# Download full logs for analysis
gh run view 789456 --log > test-failure.log

# After fixing locally, push
git add .
git commit -m "Fix test failure"
git push

# Watch new run
gh pr checks 123 --watch
```

### Example 4: Multi-Repo Coordination

**Scenario**: Feature spans multiple repos, need coordinated PRs.

```bash
# Repo 1: API changes
cd ~/code/api
git checkout -b add-v2-endpoint
# ... make changes ...
git add . && git commit -m "Add v2 endpoint"
git push -u origin add-v2-endpoint
gh pr create --title "Add v2 API endpoint" --body "Part 1/3 - API layer"

# Repo 2: Client changes
cd ~/code/client
git checkout -b use-v2-endpoint
# ... make changes ...
git add . && git commit -m "Use v2 endpoint"
git push -u origin use-v2-endpoint
gh pr create --title "Use v2 API endpoint" \
  --body "Part 2/3 - Client changes. Depends on owner/api#123"

# Repo 3: Docs
cd ~/code/docs
git checkout -b document-v2
# ... make changes ...
git add . && git commit -m "Document v2 endpoint"
git push -u origin document-v2
gh pr create --title "Document v2 endpoint" \
  --body "Part 3/3 - Documentation"

# Monitor all PRs
gh search prs --author @me --state open
```

### Example 5: Release Process

**Scenario**: Cutting a new release with changelog and assets.

```bash
# Ensure main is up to date
git checkout main
git pull

# Create release branch
git checkout -b release-v2.1.0

# Update version files
echo "2.1.0" > VERSION
git add VERSION
git commit -m "Bump version to 2.1.0"

# Generate changelog
gh pr list --state merged --search "milestone:v2.1.0" --json number,title \
  | jq -r '.[] | "- #\(.number): \(.title)"' > RELEASE_NOTES.md

git add RELEASE_NOTES.md
git commit -m "Add release notes for v2.1.0"
git push -u origin release-v2.1.0

# Create release PR
gh pr create --title "Release v2.1.0" --base main

# After approval and merge
git checkout main
git pull

# Tag release
git tag v2.1.0
git push origin v2.1.0

# Build artifacts
make build  # Creates dist/

# Create release
gh release create v2.1.0 \
  --title "Release 2.1.0" \
  --notes-file RELEASE_NOTES.md \
  dist/*

# Announce
gh release view v2.1.0 --web
```

### Example 6: Workstack + gh Integration

**Scenario**: Using workstack with GitHub PR information.

```bash
# List worktrees with PR info
workstack list

# Output:
# Worktree         Branch              PR Status
# ────────────────────────────────────────────────
# main             main                -
# feature-auth     feature-auth        #123 OPEN ✓
# feature-ui       feature-ui          #124 OPEN (draft)
# bugfix-null      bugfix-null         #125 MERGED

# Switch to worktree and view PR
workstack switch feature-auth
gh pr view

# Make changes
# ... edit files ...
git add . && git commit -m "Update"
git push

# Check if ready to merge
gh pr checks --watch

# Merge from worktree
gh pr merge --squash

# Sync worktrees (cleans up merged branches)
workstack sync

# List again - merged worktree removed
workstack list
```

### Example 7: Automation Scripts

**Scenario**: Automate common workflows with shell scripts.

```bash
#!/bin/bash
# auto-review-bot.sh - Auto-approve PRs meeting criteria

# List open PRs
PRS=$(gh pr list --json number,author,isDraft,statusCheckRollup)

# For each PR
echo "$PRS" | jq -c '.[]' | while read -r pr; do
  NUMBER=$(echo "$pr" | jq -r '.number')
  AUTHOR=$(echo "$pr" | jq -r '.author.login')
  IS_DRAFT=$(echo "$pr" | jq -r '.isDraft')

  # Skip drafts
  if [ "$IS_DRAFT" = "true" ]; then
    continue
  fi

  # Check if all checks passed
  FAILURES=$(echo "$pr" | jq '[.statusCheckRollup[] | select(.conclusion != "SUCCESS")] | length')

  # Auto-approve if by trusted author and checks pass
  if [ "$AUTHOR" = "dependabot" ] && [ "$FAILURES" = "0" ]; then
    echo "Auto-approving PR #$NUMBER from $AUTHOR"
    gh pr review "$NUMBER" --approve --body "Auto-approved by bot"
    gh pr merge "$NUMBER" --auto --squash
  fi
done
```

---

## Key Insights for AI Agents

### Mental Model Summary

1. **Stateless operation**: gh has no local cache (unlike git or Graphite)
2. **API wrapper**: Every command calls GitHub API
3. **Authentication required**: All operations need valid token
4. **JSON-first**: Design for scripting with `--json`
5. **Context-aware**: Auto-detects repo from git remote

### When to Use gh Commands

| Situation         | Command                           | Why                       |
| ----------------- | --------------------------------- | ------------------------- |
| Create PR         | `gh pr create`                    | Faster than web UI        |
| Check PR status   | `gh pr status`                    | See all relevant PRs      |
| Review PRs        | `gh pr checkout` + `gh pr review` | Full workflow in terminal |
| Monitor CI        | `gh run watch`                    | Real-time feedback        |
| Script operations | `gh api`                          | Direct API access         |
| Multi-repo work   | `gh pr list -R`                   | No need to cd             |

### Common Mistakes to Avoid

1. **Forgetting authentication**
   - Always run `gh auth status` first in new environments
   - `gh` commands silently fail if not authenticated

2. **Fetching unnecessary data**
   - `statusCheckRollup` is slow - only fetch when displaying
   - Use `--limit` to reduce API calls
   - Cache results in scripts

3. **Not using JSON output for scripting**
   - Human-readable output changes between versions
   - Always use `--json` in scripts
   - Parse with `jq` for robustness

4. **Rate limiting**
   - GitHub API: 5000 requests/hour (authenticated)
   - Batch operations when possible
   - Use GraphQL for complex queries (single request)

5. **Assuming repo context**
   - Always specify `-R` in scripts for clarity
   - Don't rely on current directory in automated contexts
   - Use `GH_REPO` environment variable for consistency

### Performance Tips

1. **Batch operations**

   ```bash
   # Bad: N API calls
   for branch in $(git branch -r); do
     gh pr view "$branch"
   done

   # Good: 1 API call
   gh pr list --json number,headRefName,state
   ```

2. **Selective field fetching**

   ```bash
   # Slow: Fetches everything
   gh pr list --json state,statusCheckRollup

   # Fast: Minimal fields
   gh pr list --json number,state
   ```

3. **Use Graphite cache when available**

   ```python
   # Workstack pattern: try cache first
   prs = graphite_ops.get_prs_from_graphite(...)
   if not prs:
       prs = github_ops.get_prs_for_repo(...)
   ```

4. **Cache API responses**
   ```bash
   # Cache for script lifetime
   PRS=$(gh pr list --json number,state)
   # ... use $PRS multiple times ...
   ```

### Scripting Best Practices

1. **Always use `--json` in scripts**

   ```bash
   # Fragile
   gh pr list | grep OPEN

   # Robust
   gh pr list --json state | jq '.[] | select(.state == "OPEN")'
   ```

2. **Check command success**

   ```bash
   if gh pr view 123 --json state > /dev/null 2>&1; then
     # PR exists
   else
     # PR doesn't exist
   fi
   ```

3. **Handle missing gh gracefully**

   ```python
   try:
       subprocess.run(["gh", "pr", "list"], check=True)
   except FileNotFoundError:
       # gh not installed - degrade gracefully
   ```

4. **Use `GH_TOKEN` for CI**
   ```bash
   # In CI environment
   export GH_TOKEN=${{ secrets.GITHUB_TOKEN }}
   gh pr create ...
   ```

### Integration Patterns

**Pattern 1: Lazy loading PR data**

```python
class WorktreeInfo:
    _pr_cache: PullRequestInfo | None = None

    def get_pr(self) -> PullRequestInfo | None:
        if self._pr_cache is None:
            self._pr_cache = github_ops.get_pr_status(...)
        return self._pr_cache
```

**Pattern 2: Error boundary**

```python
try:
    result = subprocess.run(["gh", "pr", "list"], check=True)
    return parse_prs(result.stdout)
except (subprocess.CalledProcessError, FileNotFoundError):
    # Graceful degradation
    return {}
```

**Pattern 3: Conditional fetching**

```python
if config.show_pr_info:
    prs = github_ops.get_prs_for_repo(repo, include_checks=False)
else:
    prs = {}
```

---

## Additional Resources

- **Official Manual**: https://cli.github.com/manual
- **API Documentation**: https://docs.github.com/en/rest
- **GraphQL Explorer**: https://docs.github.com/en/graphql
- **gh Releases**: https://github.com/cli/cli/releases

---

## Glossary Quick Reference

```
PR:          Pull Request (proposed changes)
Issue:       Task, bug, or feature request
Run:         Workflow execution (CI/CD)
Release:     Tagged version with assets
Gist:        Code snippet
Fork:        Personal copy of repo
Head:        Source branch of PR
Base:        Target branch of PR
Draft:       PR not ready for review
Checks:      CI/CD status
Review:      Code review (approve/request changes)
Merge:       Incorporate PR into base branch
```

---

**End of GitHub CLI Mental Model Guide**

This document provides a complete mental model for understanding and working with GitHub CLI. When in doubt, remember: **`gh` is a stateless API wrapper that brings GitHub features to your terminal, optimized for both interactive use and scripting**.
