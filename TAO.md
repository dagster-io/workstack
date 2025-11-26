# The TAO of `erk`

`erk` is a tool for the orchestration and management of plan-oriented agentic engineering.

## What is Plan-Oriented Agenetic Engineering

AI is transforming the world of software development. What started with in-IDE copilots, intelligent typeaheads, and standlone conversational chat interfaces is now evolving into a an entire new generation of tooling.

Planning has become an increasingly important modality. Widely popularized by Claude Code, it is now getting incorporated into other popular tools such as Cursor.

`erk` believes that planning is the foundational skill of agenetic engineering and that for the forseeable future will be an essential skill, even as model capabilties increase.

Planning is the way that larger units of work that can execute with higher quality outcomes. This property also means that this is the opportunity to massively increase throughput through parallelization. Without planning, you are limited to making serial chains of work more productivity via typeaheads or synchronous code generation steps.

However more problematically without planning you are unlikely to provide sufficient context to a model, leaving your instructions too open for interpretation. This is often intepreted as a hallunication, but the reality is that if insufficient context was given, there is no way for the model to fulfill your requirements. It will be forced to invent them.

Put another way: No matter how powerful they become, models cannot solve the "Garbage-In-Garbage-Out" problem. Planning is the right tool to ensure that the right context is provided to the agent by the engineer.

## The Gap: No Engineering Process, Tooling, or Workflows Around Plans

Claude Code popularized "plan mode" as a first-class capability in agentic engineerong tools. Other tools, such as Cursor and Windsurf, have since followed suit. The ecosystem clearly sees lot of uptake and process in the technique,

Yet despite this recognition, planning remains poorly integrated into actual developer workflows in pract. The primitives exist but there is no tooling but there is no coherent process that ties them together.

Engineers who want to work in a plan-oriented way face significant friction. Plans are saved as markdown files and must be managed, or exist only ephemerally in agent context. There is no system of record. Plans cannot be queried, tracked, or closed. They are not attached to any automation or workflow.

Parallel execution is similarly ad-hoc. Git worktrees provide isolation, but management around them is primitive and tedious. Developers have to manually bookkeep locations, environments, and so forth.

This is not a conceptual problem. It is an engineering and tooling problem.

## The Solution: `erk`

erk is tool centered around an opinionated workflow that unifies plans, worktrees, and compute into a coherent engineering process. It is uncompromisingly plan-oriented: you create plans, you implement plans, and the tooling is designed around that workflow.

### Plans as System of Record

In erk, plans are not files on disk or ephemeral context in an agent session. They are persisted in a system of record. In this initial version, they are GitHub issues. This means plans:

- Can be saved, listed, and tracked for bookkeping
- Integrating into engineering workflows directly, such as code review, pull requests, and
  opened, closed, and attached to pull requests.
- They are hubs of context and build up the memory of an engineering organization.

### Worktrees are as essential and well-supported as branches

Worktrees are essential to high output agentic engineering. Without worktrees (or a similar abstraction), you cannot parallelize work across multiple agents, eliminating much of the promise of the technology.

`erk` believes that worktrees are as first-class as branches in agenetic engineering workflows. They only reason why they aren't right now is because of tooling quality.

In tools like `git` and `gt`––which `erk` is built on––you checkout branches. In `erk` you checkout worktrees, which are created emphemerally and tied to a _branch_ and an _environment_.

In the initial version, the toolchain is `gt`, `git`, `uv` (Python Environment management), `gh` (for issues and automation). When you checkout a worktree, it creates or swithes to:

- A worktree
- A branch
- A virtual environment (which it syncs and activates)

With those three things in place you are free to allow agents to author code in parallel. The process is seamless.

erk manages worktrees so engineers don't have to. Creating a worktree, switching between them, and activating the correct environment happens seamlessly—as easily as checking out a branch. erk integrates with
Graphite for stacked PRs and UV for instant virtual environment activation. The friction that normally prevents parallel local execution is removed.

### Compute

Lastly agents need compute and environments to execute in parallel. And they need isolation to execute safely in an autonomous fashion. `erk` ties in this as well. By default `erk` provides isolation at the worktree and virtual environment level on your machine. This enables parallization, but does not solve security and safety issues.

As an initial remote execution engine, `erk` uses Github Actions. You can submit work to the `erk` queue as easily (more easily?) than executing on your own machine. This means you can allow tools such as claude code to execute in "dangerous" modes as Github Runners provide isolation. You are also no longer limited by the compute capacity of your laptop. You can infinitely scale physically. You are only limited by your ability to generate plans.

## Putting It All Together: The Workflow

Plan → Save → Implement → Review and Iterate → Ship

- Plan: Within your agentic tool of choice—in this case, Claude Code—you construct a plan. This is where context leaves your head and enters the system.
- Save: The plan is persisted to the system of record. In `erk`, this is a slash command that creates a tool-managed GitHub issue. The plan is now trackable, queryable, and attached to your engineering
  workflow.
- Implement: Execute the plan locally with `erk implement` or dispatch it remotely with `erk submit`. Local execution creates a worktree, activates the environment, and invokes Claude. Remote execution triggers a
  GitHub Actions workflow that creates a PR. All of this is tracked by `erk`.
- Review and Iterate. Review the code. If the output is close but not complete, seamlessly check out the worktree locally and iterate. If more substantial work is needed, issue a follow-up plan.
- Ship: Merge the PR. The plan closes automatically, leaving the issue and the PR as a permanent record of what was planned, what was done, and any discussion along the way. You clean up your mess and build up the engineering organization's memory over time.

## Current Scope

`erk` is an internal tool developed at Dagster Labs. It reflects our beliefs about how agentic engineering should work and how we want to work ourselves.

The philosophy is general, but the current implementation is opinionated and specific. To use `erk` effectively today, you need:

- `python`: Programming Language
- `claude`: Claude Code
- `uv`: Fast Python Environment Management
- `gt`: Graphite for stacked PRs
- `gh`: Github for issues, PRs, and Actions

This is the toolchain we use internally. erk is designed to be extensible to other languages, systems of record, and compute backends. Our next toolchain will be a Typescript-focused one. Beyond that we have no plans for additional stacks of tools.

If you're outside Dagster Labs and find this useful, you're welcome to explore, but will likely have challenges using the tool in your environment.

This is also meant to be a showcase and a place to interact with collaborators where we have deep partnerships and context. For broader public we will not actively fix bugs, work on features, or accept contributions that do not directly apply to the work at Dagster Labs.
