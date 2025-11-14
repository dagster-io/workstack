## Implementation Plan: Create Dagster Code Smells Skill Document

### Objective

Create a comprehensive code smells skill document in `.claude/skills` that captures all coding standards from the Dagster discussions, organized for progressive disclosure and easy reference by AI agents and developers.

### Context & Understanding

#### API/Tool Quirks

- Claude skills support markdown formatting with headers for navigation
- Skills in `.claude/skills` are automatically loaded by Claude Code
- Large skill files can impact context usage - progressive disclosure helps
- Skill files can reference each other for modular organization

#### Architectural Insights

- Separate code smells document allows dignified-python skill to remain focused on core patterns
- Progressive disclosure enables agents to load only needed sections
- Code smells are battle-tested from production systems at Dagster Labs
- Each smell documents real bugs that occurred in production

#### Domain Logic & Business Rules

- Code smells are subjective but help develop "collective taste" in engineering teams
- These patterns come from a Python-heavy codebase (Dagster) with strong typing culture
- Standards evolved from fixing real production issues, not theoretical concerns
- Trade-offs are explicitly documented - no absolutist positions

#### Complex Reasoning

- **Rejected**: Integrating all standards into existing dignified-python skill
  - Reason: Would make the skill too large and unfocused
  - Also: Mixing foundational principles with specific anti-patterns reduces clarity
- **Chosen**: Separate code-smells document with cross-references
  - Maintains separation of concerns
  - Allows progressive disclosure for context efficiency

#### Known Pitfalls

- DO NOT simply copy-paste from Dagster docs - needs reformatting for skill context
- DO NOT lose the practical examples - they're crucial for understanding
- DO NOT present rules without rationale - the "why" is as important as the "what"

#### Raw Discoveries Log

- Found 11 code smell documents plus 1 README in docs/reference/dagster-discussions
- All documents follow consistent structure with problem, explanation, examples, solutions
- Documents date from April 2024 to March 2025
- Each document references real Dagster PRs showing the fixes
- Synthesis identified 11 major categories of standards
- Parameter design has the most documents (5 files)
- Most recent addition covers context manager usage (March 2025)

#### Planning Artifacts

**Files to process:**

- 9505-code-smell-using-repr-in-programmatically-significant-ways.md
- 9509-code-smell-excessive-use-of-default-values-on-parameters.md
- 9541-code-smell-operations-that-mislead-about-their-performance-characteristics.md
- 9602-code-smell-errors-too-deep-in-the-call-stack-or-too-far-into-the-program.md
- 9682-code-smell-callsites-with-multiple-non-obvious-positional-parameters.md
- 9694-code-smell-invalid-parameter-combinations.md
- 9719-code-smell-parameter-anxiety.md
- 9753-code-smell-using-overly-specific-context-objects-in-context-agnostic-code-paths.md
- 9791-code-smell-a-god-class.md
- 9986-code-smell-too-many-local-variables.md
- 14241-code-smell-assigning-context-managers-to-variables.md

#### Implementation Risks

**Content Volume:**

- Full inclusion of all standards creates a large skill file
- May need to balance completeness with usability

**Maintenance:**

- Keeping skill synchronized with source documents if they're updated
- Ensuring examples remain relevant to current Python versions

### Implementation Steps

1. **Create skill directory structure**: Ensure `.claude/skills/` directory exists
   [CRITICAL: Use kebab-case for all Claude artifacts per workstack standards]
   - Success: Directory exists at `.claude/skills/`
   - On failure: Create with `mkdir -p .claude/skills/`

   Related Context:
   - Claude artifacts must use kebab-case per workstack AGENTS.md
   - Skills directory is standard location for Claude Code skills

2. **Create the code smells document**: Write comprehensive skill to `.claude/skills/code-smells-dagster.md`
   - Structure with clear navigation headers
   - Include table of contents for quick reference
   - Organize by categories: Function & API Design, Performance & Interfaces, Code Organization, Python-Specific
   - Include all 11 synthesized standards with examples
   - Add meta-principles section
   - Success: File created with all content properly formatted
   - On failure: Check write permissions in .claude directory

   Related Context:
   - Each standard needs DO/DON'T format, rationale, and code examples
   - Progressive disclosure through header hierarchy enables efficient loading
   - See synthesis from analysis for complete content structure

3. **Add cross-reference in dignified-python skill**: Update existing skill to reference new document
   - Add note about additional code smells document
   - Link to specific sections where relevant
   - Success: Reference added without disrupting existing content
   - On failure: Skip if dignified-python skill doesn't exist locally

   Related Context:
   - Maintains separation of concerns between core principles and specific smells
   - Allows agents to load only what they need

4. **Create quick reference guide**: Add a summary table at the top of the document
   - Map common coding scenarios to relevant rules
   - Include "If writing X, check Y" format
   - Success: Quick reference table helps agents find relevant rules fast
   - On failure: Document still usable without quick reference

   Related Context:
   - Agents need fast lookup for common scenarios
   - Table format from proposal provides good starting point

5. **Validate markdown formatting**: Ensure proper rendering
   - Check code block syntax highlighting
   - Verify header hierarchy
   - Test internal links if used
   - Success: Document renders correctly in markdown viewer
   - On failure: Fix any markdown syntax issues

   Related Context:
   - Proper formatting ensures agents can parse and navigate effectively
   - Code examples must use proper fence syntax for highlighting

### Testing

- Verify skill loads in Claude Code without errors
- Check that navigation headers provide good document structure
- Ensure code examples are syntactically valid Python
- Confirm all 11 standards are included with examples
- Final validation: Have Claude Code read and summarize the skill

---

## Progress Tracking

**Current Status:** NOT STARTED

**Last Updated:** 2025-11-14

### Implementation Progress

- [ ] Step 1: Create skill directory structure
- [ ] Step 2: Create the code smells document
- [ ] Step 3: Add cross-reference in dignified-python skill
- [ ] Step 4: Create quick reference guide
- [ ] Step 5: Validate markdown formatting

### Overall Progress

**Steps Completed:** 0 / 5
