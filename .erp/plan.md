# Optimize plan-extractor Agent: Prevent Wasteful Session File Reading

## Problem

The plan-extractor agent wasted 54s and 44k tokens reading `~/.claude/projects/*.jsonl` files unnecessarily.

**Root cause:** The agent prompt says "extract semantic understanding from conversation context" but:
- Subagents don't have access to parent conversation
- The term "conversation context" is ambiguous
- Agent interpreted this as "read session files" and wasted massive tokens

**What should happen:** The plan was already pre-extracted and passed via `plan_content`. The agent should extract context FROM the plan markdown itself, not search external files.

## Constraint

Keep model as `opus` (per user request)

## Files to Modify

1. `/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/agents/erk/plan-extractor.md`
2. `/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/save-plan.md`

## Implementation

### File 1: plan-extractor.md

#### Change 1: Add Subagent Architecture Note (after line 32)

Insert new section after "Your output is JSON only":

```markdown
## Subagent Architecture Constraints

You are a SUBAGENT with limited context access:
- You CAN read the plan content passed in the prompt
- You CAN examine codebase files for verification
- You CANNOT access the parent conversation where planning occurred
- You CANNOT read Claude session files (~/.claude/projects/*.jsonl)

"Conversation context" in this document means the plan markdown content itself and your current conversation - NOT the parent planning conversation or session files.
```

#### Change 2: Update Step 1, Case 1 (around line 76)

Change:
```
Your job: Apply guidance, extract context from conversation, ask questions, return enhanced plan.
```

To:
```
Your job: Apply guidance, extract context from plan content, ask questions, return enhanced plan.

**CRITICAL:** Do NOT read session files. Context extraction means analyzing the plan markdown itself, not searching ~/.claude/projects/. The plan was already extracted by the calling command.
```

#### Change 3: Update Step 1, Case 2 (around line 104)

Change:
```
Your job: Find plan in conversation, apply guidance, extract context, ask questions, return enhanced plan.
```

To:
```
Your job: Find plan in your conversation history (the messages in THIS conversation thread), apply guidance, extract context from plan, ask questions, return enhanced plan.

**CRITICAL:** Do NOT read ~/.claude/projects/*.jsonl files. Search your current conversation messages only.
```

#### Change 4: Update Step 4 introduction (around line 220)

Change:
```
Analyze the planning discussion to extract valuable context.
```

To:
```
Analyze the plan content to extract valuable context embedded during planning. Extract context from the plan markdown itself - NOT from session files or parent conversation.

**CRITICAL:** Do NOT read session files or try to access the parent planning conversation. Work with the plan content you received.
```

#### Change 5: Add Best Practice (after line 523)

Add new section:

```markdown
### Never Read Session Files

The plan was already extracted from session logs by the calling command.

```bash
# WRONG - Wastes tokens and time
cat ~/.claude/projects/-Users-*/session-*.jsonl
grep "ExitPlanMode" ~/.claude/projects/*.jsonl

# CORRECT - Context comes from plan_content
# Analyze the plan markdown passed in the prompt
```

Session file reading caused 54s delays and 44k wasted tokens. All needed context is in the plan_content you received.
```

### File 2: save-plan.md

#### Change 1: Update prompt in Step 2 (lines 237-241)

Change `from conversation context` to `from the plan content` in:
```
3. Extract semantic understanding (8 categories) from conversation context
```

#### Change 2: Update fallback prompt (lines 249-252)

Change:
```
Session log extraction failed. Search conversation context for implementation plan.
```

To:
```
Session log extraction failed. Search YOUR conversation messages for implementation plan (not session files).
```

#### Change 3: Update "What the agent does" (lines 264, 271)

Change both instances of:
```
4. Extracts semantic understanding (8 categories) from conversation
```

To:
```
4. Extracts semantic understanding (8 categories) from plan content
```

## Expected Outcomes

- Eliminate 54s delays from reading large session files
- Save ~44k tokens per invocation
- Same quality output (8 context categories extracted from plan content)
- Agent can still read codebase files when needed for verification

## Context & Understanding

### Architectural Insights

- **Subagent isolation**: Subagents launched via Task tool do NOT have access to the parent conversation context. This is a fundamental architectural constraint that the original prompt failed to account for.
- **Pre-extraction pattern**: The calling command (`save-plan.md`) extracts the plan via kit CLI BEFORE launching the agent. This separation is intentional - mechanical extraction (kit CLI) vs semantic enrichment (agent).
- **"Conversation context" ambiguity**: In a subagent, "conversation" can mean either (1) the current subagent conversation or (2) the parent planning conversation. The original prompt was ambiguous, leading to the agent attempting to access parent conversation via session files.

### Known Pitfalls

- **Session file reading trap**: When told to "extract from conversation," an agent without conversation access may attempt to read `~/.claude/projects/*.jsonl` files to reconstruct context. This is wasteful because:
  - Session files are large (can be megabytes)
  - Parsing JSONL is expensive in tokens
  - The needed information was already extracted and passed in the prompt
- **Ambiguous terminology**: Terms like "conversation context" must be explicit about WHICH conversation in multi-agent architectures.

### Domain Logic & Business Rules

- **Token economy**: 44k wasted tokens per invocation is significant cost. Eliminating this is a direct cost savings.
- **Latency budget**: 54s delay is unacceptable for an interactive CLI tool. This optimization directly improves UX.
- **Model constraint**: Keep model as `opus` per user request - this is an explicit requirement from the planning discussion.

### Implementation Risks

- **Low risk**: Changes are documentation/prompt updates only - no code logic changes.
- **Behavioral change**: Agent behavior will change, but the intent is to PREVENT an undesired behavior (session file reading), not change the core functionality.
- **Regression risk**: Minimal - the changes add explicit prohibitions and clarifications, they don't remove any capabilities.

### Raw Discoveries Log

- plan-extractor agent is located at `/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/agents/erk/plan-extractor.md`
- save-plan command is located at `/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/save-plan.md`
- Line numbers verified against actual file content (lines 31-32, 88, 104, 220-222 all match expected content)
- Agent has `tools: Read, Bash, AskUserQuestion` in YAML front matter (line 6)
- Agent explicitly lacks Edit/Write tools - structural enforcement

### Planning Artifacts

- Read full `plan-extractor.md` (579 lines) to verify structure and line numbers
- Read full `save-plan.md` (574 lines) to understand orchestration flow
- Verified specific line ranges for each proposed change
- Confirmed architecture note insertion point (after line 32)
- Confirmed best practice insertion point (after line 523)

### API/Tool Quirks

- **Task tool isolation**: Subagents launched via Task tool receive only the prompt provided - they cannot see parent conversation history. This is by design for security/isolation.

### Complex Reasoning

- **Why not just remove Read/Bash access?**: The agent legitimately needs Read access to verify codebase patterns and Bash for git/kit CLI commands. The solution is to clarify WHAT to read, not remove reading capability entirely.
- **Why multiple CRITICAL warnings?**: The original behavior was persistent - adding multiple explicit prohibitions at different points in the workflow ensures the agent cannot misinterpret at any step.
