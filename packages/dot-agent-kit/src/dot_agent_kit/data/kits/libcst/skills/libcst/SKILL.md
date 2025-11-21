# LibCST Refactoring Skill

**Use this skill for**: Generating LibCST transformation code for systematic Python refactoring.

## Purpose

This skill provides battle-tested patterns for creating LibCST transformation scripts that perform precise Python refactoring across multiple files.

## When to Load This Skill

Load this skill when you need to:

- Generate LibCST transformation code
- Understand LibCST transformation patterns
- Create surgical Python refactoring scripts
- Perform batch operations across multiple Python files

## Documentation Structure

This skill contains comprehensive LibCST transformation guidance:

1. **guide.md**: Core principles and battle-tested patterns
   - 6 Critical Success Principles
   - Pre-flight checklist
   - Script templates
   - Common pitfalls

2. **patterns.md**: Comprehensive pattern reference
   - Specific transformation examples
   - Matcher patterns
   - Code snippets for common operations

## Loading Instructions

When you need to generate LibCST transformation code:

1. Read `@.claude/docs/libcst-refactor/guide.md` for core principles
2. Read `@.claude/docs/libcst-refactor/patterns.md` for specific patterns
3. Generate transformation code following the templates

## Key Principles (Quick Reference)

1. **Visualize FIRST, Code SECOND** - Use `python -m libcst.tool print` to see CST structure
2. **Use matchers for selection** - `m.Call()`, `m.Name()`, not `isinstance()`
3. **Return updated_node** - Never modify in place
4. **Chains don't fail silently** - Check `m.matches(node, pattern)` carefully
5. **Preserve formatting with `with_changes()`** - Don't reconstruct from scratch
6. **Test incrementally** - Start with one file, expand gradually

## Integration with Kit CLI

The libcst kit provides an `execute` command that safely runs generated transformation code:

```bash
# Generate transformation code using this skill
# Then execute via kit CLI:
echo "$generated_code" | dot-agent run libcst execute --files "src/**/*.py" --dry-run
```

The generated code should:

- Output JSON results
- Check `DRY_RUN` environment variable
- Handle errors gracefully
- Follow the templates from guide.md

---

**Remember**: This skill provides the knowledge for generating transformations. The kit CLI command (`dot-agent run libcst:execute`) handles safe execution.
