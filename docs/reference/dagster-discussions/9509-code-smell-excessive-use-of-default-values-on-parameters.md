---
discussion_number: 9509
title: "Code Smell: Excessive use of default values on parameters"
author: schrockn
created_at: 2024-04-30T14:38:39Z
updated_at: 2024-04-30T17:58:16Z
url: https://github.com/dagster-io/internal/discussions/9509
category: Python Code Smells and Anti-Patterns
---

# Do not excessively use default values on argument parameters

Our codebase has many functions that 1) take lots of parameters and 2) provide default values for their parameters. Often, this is the wrong thing to do, and leads to brittle and dangerous code.

In a system like Dagster, there is often a lot of "schlepping" code, where functions exist to organize code and business logic and will not have many call sites. They take parameters, do some business logic, and then schlepp parameters down the stack. We can distinguish this from functions that are libraries or utilities and will have many call sites.

For "schlepping" code, providing default values is usually the wrong thing to do.

An example is helpful.

Take `_logged_execute_job`:

```python
@telemetry_wrapper
def _logged_execute_job(
    job_arg: Union[IJob, JobDefinition],
    instance: DagsterInstance,
    run_config: Optional[Mapping[str, object]] = None,
    tags: Optional[Mapping[str, str]] = None,
    op_selection: Optional[Sequence[str]] = None,
    raise_on_error: bool = True,
    asset_selection: Optional[Sequence[AssetKey]] = None,
) -> JobExecutionResult:
```

There is *no* reason why `asset_selection` should default to `None`. It is brittle and dangerous because the behavior `None` signifies that one should execute *everything* that is in scope. This "pattern" is everywhere in the codebase.

This means that is someone adds a call site they can easily make the mistake of _omitting_ the selection parameters and then executing everything. This is a dangerous mistake to make, and we have made it. We have through casual oversight forgotten to thread through a selection from the UI all the way to our core framework, missed a single function call, ignoring the passed in user selection, and instead executed everything. This is a very, very bad bug that is all too easy to introduce in these code paths.

Instead you should bias towards _requiring_ the argument, even if you force callsites to pass in `None` explicitly. At least that way that consumer of the function has had to make address the meaning of the argument, and explicitly set it. This slight friction is orders of magnitude cheaper than pushing difficult-to-detect, dangerous bugs.