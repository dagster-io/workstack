## Pattern Detection & Reference Loading

When you detect these patterns in code, load the corresponding reference file:

| Pattern Detected                                                       | Load Reference                                                                   |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `try:`, `except:`, exception handling                                  | → Load `@.claude/docs/dignified-python/exception-handling.md`                    |
| Type hints: `List[`, `Dict[`, `Optional[`, `Union[`, `from __future__` | → Load `@.claude/docs/dignified-python/version-specific/310/type-annotations.md` |
| `path.resolve()`, `path.is_relative_to()`, `Path(`, pathlib operations | → Load `@.claude/docs/dignified-python/path-operations.md`                       |
| `Protocol`, `ABC`, `abstractmethod`, interfaces                        | → Load `@.claude/docs/dignified-python/dependency-injection.md`                  |
| Import statements, `from .`, relative imports                          | → Load `@.claude/docs/dignified-python/imports.md`                               |
| `click.`, `@click.`, CLI commands, `print()` in CLI                    | → Load `@.claude/docs/dignified-python/cli-patterns.md`                          |
| `subprocess.run`, `subprocess.Popen`, shell commands                   | → Load `@.claude/docs/dignified-python/subprocess.md`                            |
| Code review, refactoring, complexity analysis                          | → Reference `.claude/docs/code-review/` (manual, not auto-loaded)                |
| Need core standards                                                    | → Load `@.claude/docs/dignified-python/core-standards-universal.md`              |
| Need implementation examples                                           | → Reference `.claude/docs/code-review/patterns-reference-universal.md` (manual)  |
