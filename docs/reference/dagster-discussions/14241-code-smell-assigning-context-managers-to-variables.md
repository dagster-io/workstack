---
discussion_number: 14241
title: "Code Smell: Assigning Context Managers to Variables"
author: schrockn
created_at: 2025-03-09T20:04:47Z
updated_at: 2025-03-10T09:20:12Z
url: https://github.com/dagster-io/internal/discussions/14241
category: Python Code Smells and Anti-Patterns
---

## Avoid assigning context managers to variables for later invocation

Sometimes it is tempting or seems necessary to assign a Python `contextmanager` return value to a temporary variable or instance, only to be called with `with` (or perhaps even directly using the `contentmanager` protocol with `__enter__` and `__exit__` layer).

While this isn’t _always_ a bad thing, it should be viewed with suspicion. This can usually be refactored to use functional decomposition to accomplish the same thing, and the result is safer, more reliable code.

### Case Study:

Take https://github.com/dagster-io/dagster/pull/28341 as an example. This is a problem in the logic where a temporary workspace (a heavyweight operation) always occurred. The means `dg check defs` launched a code server unncessarily and the command is noisier and slower than it should have been.

The bug blamed to https://github.com/dagster-io/dagster/pull/28172 but the code pattern originated in https://github.com/dagster-io/dagster/pull/27873.

You’ll note that `temp_workspace_file_cm` is assigned and then only _later_ is it passed to `with`.

```python
  # In a code location context, we can just run `dagster definitions validate` directly, using `dagster` from the
  # code location's environment.
  if dg_context.is_project:
      cmd = ["uv", "run", "dagster", "definitions", "validate", *forward_options]
      cmd_location = dg_context.get_executable("dagster")
      temp_workspace_file_cm = nullcontext()

  # In a deployment context, dg validate will construct a temporary
  # workspace file that points at all defined code locations and invoke:
  #
  #     uv tool run --with dagster-webserver dagster definitions validate
  elif dg_context.is_workspace:
      cmd = [
          "uv",
          "tool",
          "run",
          "dagster",
          "definitions",
          "validate",
          *forward_options,
      ]
      cmd_location = "ephemeral dagster definitions validate"
      temp_workspace_file_cm = temp_workspace_file(dg_context)
  else:
      exit_with_error("This command must be run inside a code location or deployment directory.")

  with pushd(dg_context.root_path), temp_workspace_file_cm as workspace_file:
      print(f"Using {cmd_location}")  # noqa: T201

      if workspace_file:  # only non-None deployment context
          cmd.extend(["--workspace", workspace_file])

      print(" ".join(cmd))  # noqa: T201

      result = subprocess.run(cmd, check=False)
```

This is a recipe for problems:

- It is easy to write a code path later that forgets to invoke it `with`.
- It is also non-standard, non-idiomatic Python that will surprise the next engineer that wanders through the code.
- It also introduces a layer of indirection and distance between the `with` invocation and the functions.
- In this case, requires the use of the fairly magical `nullcontext` or "dummy" functions that mimic context managers in other ways.

### Tactics for resolving

In most cases, the most straightforward solution is to extract the logic into another function that is itself a `contextmanager` and compose the logic. They are designed to compose. Take advantage of that.

It generally results in a little more code, but is more obvious, easier to read, and harder to screw up. This is a tradeoff that you should take every time. Do not sacrifice correctness for brevity.

In this example the resolution to was change the code to have a `contextmanager` function that returns the data needed to successfully call `subprocess.run`, and put it next to the `pushd` call. Instead of having a temporary context manager variable, there is a codepath within that function that invokes `temp_workspace_file` within a `with` block in one case, and just uses `None` in another. No `nullcontext` necessary:

```python
with (
    pushd(dg_context.root_path),
    create_validate_cmd(dg_context, forward_options) as (cmd_location, cmd, workspace_file),
):
    print(f"Using {cmd_location}")  # noqa: T201
    if workspace_file:  # only non-None deployment context
        cmd.extend(["--workspace", workspace_file])

    print(" ".join(cmd))  # noqa: T201

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)

    click.echo("All definitions loaded successfully.")

class CommandArgs(NamedTuple):
    cmd_location: str
    cmd: list[str]
    workspace_file: Optional[str]

@contextlib.contextmanager
def create_validate_cmd(dg_context: DgContext, forward_options: list[str]) -> Iterator[CommandArgs]:
    if dg_context.is_project:
        # In a code location context, we can just run `dagster definitions validate` directly, using `dagster` from the
        # code location's environment.
        cmd = ["uv", "run", "dagster", "definitions", "validate", *forward_options]
        cmd_location = dg_context.get_executable("dagster")
        yield CommandArgs(cmd_location=str(cmd_location), cmd=cmd, workspace_file=None)
    elif dg_context.is_workspace:
        # In a workspace context, dg validate will construct a temporary
        # workspace file that points at all defined code locations and invoke:
        #
        #     uv tool run --with dagster-webserver dagster definitions validate
        with create_temp_workspace_file(dg_context) as temp_workspace_file:
            yield CommandArgs(
                cmd=[
                    "uv",
                    "tool",
                    "run",
                    "dagster",
                    "definitions",
                    "validate",
                    *forward_options,
                ],
                cmd_location="ephemeral dagster definitions validate",
                workspace_file=temp_workspace_file,
            )
    else:
        exit_with_error("This command must be run inside a code location or deployment directory.")
```

As a general rule, in most code paths, you should be leveraging `with` as it is meant to be used, in which case that context manager instance is completely managed by the language, rather than you.
