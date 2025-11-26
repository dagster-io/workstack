# GitHub Plan Extraction Architecture

## Overview

This document describes the architecture for extracting plans from GitHub issues, focusing on how objects are linked and the data flow.

## Schema Versions

### Schema v1 (Legacy)

- Plan content stored directly in issue body
- Simple but inefficient for metadata queries

### Schema v2 (Current)

- Issue body contains only compact metadata (YAML in HTML details block)
- Plan content stored in **first comment** wrapped with markers
- Enables fast metadata-only queries without fetching large plan content

## Object Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHubPlanStore                         │
│  (packages/erk-shared/src/erk_shared/plan_store/github.py)  │
│                                                             │
│  - Wraps GitHubIssues ABC                                   │
│  - Converts IssueInfo → Plan (provider-agnostic)            │
│  - Handles schema v1/v2 detection and extraction            │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ uses
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     GitHubIssues (ABC)                      │
│  (packages/erk-shared/src/erk_shared/github/issues/abc.py)  │
│                                                             │
│  Abstract methods:                                          │
│  - get_issue(repo_root, number) → IssueInfo                 │
│  - get_issue_comments(repo_root, number) → list[str]        │
│  - create_issue(), add_comment(), list_issues(), etc.       │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ RealGitHubIssues│ │ FakeGitHubIssues│ │ DryRunGitHub... │
│                 │ │                 │ │   (if exists)   │
│ Uses gh CLI     │ │ In-memory state │ │                 │
│ subprocess      │ │ for testing     │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Data Types

### IssueInfo

```python
@dataclass(frozen=True)
class IssueInfo:
    number: int
    title: str
    body: str           # Issue body (metadata in v2)
    state: str          # "OPEN" or "CLOSED"
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime
```

### Plan (Provider-Agnostic)

```python
@dataclass(frozen=True)
class Plan:
    plan_identifier: str  # e.g., "42" (issue number as string)
    title: str
    body: str             # Actual plan content (extracted)
    state: PlanState      # OPEN or CLOSED (enum)
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict        # {"number": 42} for GitHub
```

## Plan Extraction Workflow (Schema v2)

```
                    ┌─────────────────┐
                    │ GitHubPlanStore │
                    │   .get_plan()   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐      ┌───────────┐
    │ get_issue │      │get_issue_ │      │  extract_ │
    │  (body)   │      │ comments  │      │plan_from_ │
    │           │      │           │      │ comment   │
    └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
          │                  │                  │
          ▼                  ▼                  │
    ┌───────────┐      ┌───────────┐            │
    │ Metadata  │      │ Comments  │            │
    │   only    │      │  list[str]│────────────┘
    │  (YAML)   │      │           │       uses regex
    └───────────┘      └───────────┘       to extract
                             │
                             ▼
                       ┌───────────┐
                       │ First     │
                       │ comment   │
                       │ (plan)    │
                       └───────────┘
```

## The Bug Location

### Where

`RealGitHubIssues.get_issue_comments()` in:
`packages/erk-shared/src/erk_shared/github/issues/real.py:139-157`

### Current (Buggy) Implementation

```python
def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
    cmd = [
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
        "--jq", ".[].body",  # ← Outputs each body on its own line
    ]
    stdout = execute_gh_command(cmd, repo_root)

    if not stdout.strip():
        return []

    return stdout.strip().split("\n")  # ← BUG: Splits on ALL newlines
```

### Problem

- `jq ".[].body"` outputs each comment body followed by a newline separator
- Comment bodies containing newlines (markdown always does) get mixed with separators
- `split("\n")` treats EVERY newline as a comment separator
- Result: A 299-line comment becomes 299 "comments"

### Impact on Schema v2 Extraction

```
                    ┌─────────────────────────────┐
                    │        First Comment        │
                    │  <!-- erk:plan-content -->  │
                    │  # Plan Title               │
                    │                             │
                    │  ## Step 1                  │
                    │  Details...                 │
                    │  <!-- /erk:plan-content --> │
                    └─────────────────────────────┘
                                │
                    split("\n") │ BUG!
                                ▼
    ┌──────────────────────────────────────────────────────┐
    │  "comments" list after buggy split:                  │
    │  [                                                   │
    │    "<!-- erk:plan-content -->",  ← comments[0]       │
    │    "# Plan Title",                                   │
    │    "",                                               │
    │    "## Step 1",                                      │
    │    "Details...",                                     │
    │    "<!-- /erk:plan-content -->"                      │
    │  ]                                                   │
    └──────────────────────────────────────────────────────┘
                                │
                                ▼
    ┌──────────────────────────────────────────────────────┐
    │  extract_plan_from_comment(comments[0])              │
    │                                                      │
    │  Input: "<!-- erk:plan-content -->"                  │
    │                                                      │
    │  Regex needs BOTH markers in same string:            │
    │  r"<!-- erk:plan-content -->.*<!-- /erk:plan-content │
    │                                                      │
    │  Result: None (no match - end marker missing!)       │
    └──────────────────────────────────────────────────────┘
                                │
                                ▼
    ┌──────────────────────────────────────────────────────┐
    │  Fallback to issue body (metadata only)              │
    │                                                      │
    │  Plan.body = issue.body = metadata YAML              │
    │  (NOT the actual plan content!)                      │
    └──────────────────────────────────────────────────────┘
```

## The Fix

### Fixed Implementation

```python
def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
    cmd = [
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
        "--jq", "[.[].body]",  # ← Wrap in JSON array
    ]
    stdout = execute_gh_command(cmd, repo_root)

    if not stdout.strip():
        return []

    return json.loads(stdout)  # ← Parse as JSON array
```

### Why JSON Array Works

```
jq "[.[].body]" output:
["Line 1\nLine 2\nLine 3", "Comment 2 body"]
       ↑
Newlines within strings are escaped as \n
Array brackets clearly delimit each comment

json.loads() correctly parses:
["Line 1\nLine 2\nLine 3", "Comment 2 body"]
    ↓
[
  "Line 1\nLine 2\nLine 3",  # One comment, newlines preserved
  "Comment 2 body"           # Second comment
]
```

## Testing Architecture (5-Layer Strategy)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Business Logic Tests (70% - GitHubPlanStore)       │
│                                                             │
│ tests/integration/plan_store/test_github_plan_store.py      │
│ - Uses FakeGitHubIssues with comments pre-configured        │
│ - Tests schema v2 extraction with multi-line comments       │
│ - Tests fallback to issue body (schema v1)                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Integration Tests (10% - RealGitHubIssues)         │
│                                                             │
│ tests/integration/test_real_github_issues.py                │
│ - Uses monkeypatch to mock subprocess.run                   │
│ - Tests JSON array parsing with multi-line bodies           │
│ - Tests command structure (jq expression uses [.[].body])   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Fake Tests (5% - FakeGitHubIssues)                 │
│                                                             │
│ tests/unit/fakes/test_fake_github_issues.py                 │
│ - Tests FakeGitHubIssues correctly returns configured       │
│   comments via get_issue_comments()                         │
│ - Already exists and passes                                 │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File                                                       | Purpose                                             |
| ---------------------------------------------------------- | --------------------------------------------------- |
| `packages/erk-shared/src/erk_shared/github/issues/real.py` | **THE BUG** - RealGitHubIssues.get_issue_comments() |
| `packages/erk-shared/src/erk_shared/github/issues/fake.py` | FakeGitHubIssues for testing                        |
| `packages/erk-shared/src/erk_shared/github/issues/abc.py`  | GitHubIssues ABC interface                          |
| `packages/erk-shared/src/erk_shared/plan_store/github.py`  | GitHubPlanStore using GitHubIssues                  |
| `packages/erk-shared/src/erk_shared/github/metadata.py`    | extract_plan_from_comment() regex                   |

## Metadata Functions

### extract_plan_from_comment()

```python
def extract_plan_from_comment(comment_body: str) -> str | None:
    """Extract plan content from a comment with markers."""
    pattern = r"<!-- erk:plan-content -->\s*(.*?)\s*<!-- /erk:plan-content -->"
    match = re.search(pattern, comment_body, re.DOTALL)

    if match is None:
        return None

    return match.group(1).strip()
```

**Note**: The regex is correct! It uses `re.DOTALL` so `.` matches newlines. The bug is that the input string (from `get_issue_comments()`) doesn't contain both markers when comments are incorrectly split.

### wrap_plan_in_markers()

```python
def wrap_plan_in_markers(plan_content: str) -> str:
    """Wrap plan content in markers for storage in comment."""
    return f"""<!-- erk:plan-content -->
{plan_content.strip()}

<!-- /erk:plan-content -->"""
```
