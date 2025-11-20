## Pattern Detection & Reference Loading

When you detect these patterns in code, load the corresponding reference file:

| Pattern Detected                                                                              | Load Reference                                                                     |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `try:`, `except:`, exception handling                                                         | → Load `../../../dignified-python-shared/exception-handling.md`                    |
| Type hints: `List[`, `Dict[`, `Optional[`, `Union[`, `from __future__`, `Self`, `def func[T]` | → Load `../../../dignified-python-shared/type-annotations/type-annotations-312.md` |
| `path.resolve()`, `path.is_relative_to()`, `Path(`, pathlib operations                        | → Load `../../../dignified-python-shared/path-operations.md`                       |
| `Protocol`, `ABC`, `abstractmethod`, interfaces                                               | → Load `../../../dignified-python-shared/dependency-injection.md`                  |
| Import statements, `from .`, relative imports                                                 | → Load `../../../dignified-python-shared/imports.md`                               |
| `click.`, `@click.`, CLI commands, `print()` in CLI                                           | → Load `../../../dignified-python-shared/cli-patterns.md`                          |
| `subprocess.run`, `subprocess.Popen`, shell commands                                          | → Load `../../../dignified-python-shared/subprocess.md`                            |
| 10+ parameters, 50+ methods, context objects, code complexity                                 | → Load `../../../dignified-python-shared/code-smells-dagster.md`                   |
| Need core standards                                                                           | → Load `../../../dignified-python-shared/core-standards-universal.md`              |
| Need implementation examples                                                                  | → Load `../../../dignified-python-shared/patterns-reference-universal.md`          |
