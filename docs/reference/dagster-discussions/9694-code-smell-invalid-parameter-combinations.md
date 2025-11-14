---
discussion_number: 9694
title: "Code Smell: Invalid parameter combinations"
author: schrockn
created_at: 2024-05-12T15:22:16Z
updated_at: 2024-05-13T10:06:53Z
url: https://github.com/dagster-io/internal/discussions/9694
category: Python Code Smells and Anti-Patterns
---

## Avoid writing functions with invalid parameter states

We have an unfortunate number of functions in the code base that have optional arguments that fail if you pass certain combinations of them. There are a number of problems with it.

The obvious first problem is that code can fail at runtime through parameter combinations that pass typechecks. Another more subtle problem is that it makes future changes more difficult, thrashy, and risky.

Here is a contrived example:

```python
def takes_int_or_string(num: Optional[int], string: Optional[str]) -> None:
    if num is None and string is None:
        raise Exception("Must pass one of num or string ")
    if num is not None or string is not None:
        raise Exception("Cannot pass both num and string")
```

Better would be:

```python
def takes_union(num_or_string: Union[str, int]) -> None:
    if isinstance(num_or_string, int):
        num = num_or_string
    else:
        string = num_or_string
```

The typechecker does all the work for us. `num` is int; `string` is `str`. No runtime checks are needed, and there are no invalid states.

While a variable called `num_or_string` is not aesthetic, it is better to be proveably correct. `takes_int_or_string` is an example of "Putting Aesthetics Ahead of Correctness" (link once smell exist).

We violate this in our code and it causes real problems. Take this example from `ReconstructableJob.get_subset`

```python
# in ReconstructableJob
def get_subset(
    self,
    *,
    op_selection: Optional[Iterable[str]] = None,
    asset_selection: Optional[AbstractSet[AssetKey]] = None,
    asset_check_selection: Optional[AbstractSet[AssetCheckKey]] = None,
) -> "ReconstructableJob":
    if op_selection and (asset_selection or asset_check_selection):
        check.failed(
            "op_selection and asset_selection or asset_check_selection cannot both be provided"
            " as arguments",
        )
    op_selection = set(op_selection) if op_selection else None
    ...
```

You can specify one `asset_selection` or `asset_check_selection` unless you specify `op_selection`, in which case both `asset_selection` and `asset_check_selection` must be `None`.

This is particularly toxic example since it also violates [Excessive use of default values on parameters](https://github.com/dagster-io/internal/discussions/9509). If one makes the mistake of fixing the error by setting the offending argument to `None`, you could easily create a job that targets _all_ entities in the graph. This is fragile and dangerous.

Had we dogmatically followed this smell this never would have occured, even incrementally.

Instead when we added `asset_selection` we could have added a new object such as:

```python
class ExecutionSelection:
    # * Violating this rule once is better than doing it N times.
    # * Idiomatically, AbstractSet[AssetKey] and Iterable[str] not distinct enough to use Union.
    # * Neither defaults to None so callsites must be explicit.
    def __init__(self, asset_selection: Optional[AbstractSet[AssetKey]], op_selection: Optional[Iterable[str]]):
        # do runtime checks to ensure that one of them and not both have valid values
        self._asset_selection = asset_selection
        self._op_selection = set(op_selection) if op_selection else None
```

And use that to thread down the callstack.

`get_subset` would have ended up in the following signature.

```python
# in ReconstructableJob
def get_subset(self, execution_selection: ExecutionSelection) -> "ReconstructableJob":
    ...
```

This function is obvious and less error prone. Later when adding `asset_check_selection` it would have just required adding an item to `ExecutionSelection` without altering anything that shuffled that object down the call stack. We had to do that when adding asset checks and it was painful. An object like this composes much more effectively.

To summarize, invalid parameter combinations are a code smell. Parameters typed as `Union` or a value object to capture all said parameters is preferable, leveraging the type system for correctness and composing so that future changes are easier.
