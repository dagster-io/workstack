# The Tao of `erk`

## I. The Thesis: Plan-Oriented Development

**Core claim:** Planning is the right paradigm for agentic engineering. It is the essential technique from going from vibecoding to agenetic engineering.

- Planning extracts context from the developer's head into tokens the agent can use
- Fundamentally different from IDE + autocomplete paradigm
- Planning is a "best of both worlds" technique leading to better outcomes:
  - **Quality**: Right context leads to accurate implementation of meaningful work units
  - **Throughput**: Only planning enables parallelization of autonomous, long-running work
- Future-proof: Better models will not magically solve coding: GIGO problem persists regardless of model capability—models always need the right context. Models are powerful, but they are not clairvoyant.

## II. The Innovation Gap

**Plan mode exists, but adoption hasn't followed.**

- Claude Code pioneered and popularized plan mode
- Others (Cursor) have followed
- Despite validation, planning hasn't achieved mass adoption
- **Root cause: tooling, not concept**

## III. The Problem with Current Tooling

**Primitives exist. Orchestration and workflow doesn't.**

- Building blocks available: plan mode, git worktrees, graphite stacks, fast environment management (e.g. uv), more powerful models
- But orchestrating between them is painful:
  - Manual markdown file management
  - Manual worktree creation and navigation
  - Manual environment management across parallel workstreams
- Pain is so acute it limits developer control over agents
- This pain is especially acute for senior engineers, who want expert tools, observability, and control.

## IV. The Way of `erk`: Unify Plans + Worktrees + Compute + Workflows

**An opinionated, uncompromisingly plan-oriented workflow.**

### Pillar 1: Plans as System of Record

- Plans are not ephemeral files or agent context
- In initial version, persisted as GitHub issues
- Amenable to tooling: queryable, listable, trackable,
- Attached to workflows: PRs, automation, integrations via API access
- Hubs of context. You can attach arbitrary context to them useful for agenetic programming sessions.

### Pillar 2: Programmatic Worktrees

- Seamless creation and switching (as easy as branch switching)
- Manages locations, directories, environment hooks
- Enables parallel local execution environments
- For the initial stack: Graphite for (stacked PRs), UV for env management, (instant venv activation), git for branches and worktrees

### Pillar 3: Execution

- Local Execution happens on a per-worktree, per-environment basis.
- With worktress agents do not overwrite eachother.
- Plans know what worktrees they are associated with.

- Remote execution happens in github
- Dispatch plans to execute remotely via GitHub Actions
- Developer constructs plans in parallel, dispatches them
- Returns complete/near-complete PRs
- There is no magic bullet. Often you need to do the "last mile" of engineering yourself. Erk supports seamless local checkout for iteration to completion. `erk checkout PR` gets you a local branch and environment instantaneously

## V. The Cycle

```
Plan → Save → Implement → Ship → Close
```

- Issue becomes permanent audit trail
- Enables observability, evals, future tooling

## VI. Current Path

**Philosophy is universal. First implementation is opinionated.**

- Designed to be language/toolchain agnostic
- First showcase: Python + Claude Code + UV + Graphite
