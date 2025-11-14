---
discussion_number: 9541
title: "Code smell: Operations that mislead about their performance characteristics"
author: schrockn
created_at: 2024-05-02T12:56:28Z
updated_at: 2024-05-02T13:08:01Z
url: https://github.com/dagster-io/internal/discussions/9541
category: Python Code Smells and Anti-Patterns
---

## Do not write expensive functions when user expect them to be cheap (e.g. `@property`, `__len__`)

Python has a built-in feature for user-defined properties: `@property`. Rather than just access a raw field, a user can use property access syntax to invoke arbitrary computation.

e.g,

```python
class ListWrapper:
    def __init__(self, some_list) -> None:
        self._some_list = some_list

    @property
    def size(self) -> int:
        return len(self._some_list)
        
print(ListWrapper([1, 2, 3]).size)
```
 
While convenient this can be dangerous. The code backing this property can do anything: I/O, computationally expensive things, etc. Engineers reasonably assume that property access is cheap (a modest number of assembly instructions) and wouldn't expect that to be expensive. Further more they expect them to be cached if they are even moderately expensive, and therefore wouldn't think twice about accessing them in a loop.

We do not follow this advice all the time, and it can cause unexpected performance problems.

### Case study: `AssetSubset.size`

For example in `AssetSubset` there is a size property than in turn calls `len` on a `PartitionsSubset`:

```python
    @property
    def size(self) -> int:
        if not self.is_partitioned:
            return int(self.bool_value)
        else:
            return len(self.subset_value)
```

`PartitionsSubset` has many subclasses and they each have their own implementation of `__len__`. Different codepaths of the different subtypes lead down even deeper in our codepaths. Some end up calling `get_partition_keys` on `PartitionsDefinitions` which can be very expensive (database fetches in the case of dynamic partitions!).

_Note: `get_partitions_key` is another instance of the [Dangerous Default Value for Parameter](https://github.com/dagster-io/internal/discussions/9509) smell as the `current_time` is not required (as of this writing on 2024-05-02). Once can call this function without supplying the correct current time, and it will dutifully create a new datetime object via `now`, leading to multiple representations of current time in the same process._

In the case of time-based partitioning, we are also in bad shape. In the case of `TimeWindowPartitionsSubset` this will lead materializing _all_ the partition keys via `get_partition_keys_in_time_window` on its underlying `PartitionsDefinition`. For a customer like Discord, this means 10s of 1000s of partition keys iterated through using the `cron_string_iterator` function. This can be *extremely* expensive And all this work is done in the service of a _single_ call to the seemingly innocuous and inexpensive-looking `size` property. This kind of sloppiness leads to real product consequences. We have limits on time-based partitioning (we say we support only up to 25K partitions) and these unforced errors are a contributing factor as to why.

### Guidelines

1. Cheap-looking operations, in the common case, should never (except in unusual circumstances) lead to I/O or similarly expensive operations.
2. If access is moderately expensive, strongly consider the use of [`cached_property`](https://docs.python.org/3/library/functools.html#functools.cached_property). You can classify "moderately expensive" as "it would meaningful show up in a profiler if accessed many times."  _Note: Cached properties are only truly safe when used on an immutable class, so as a general rule do not use them against mutable classes._

