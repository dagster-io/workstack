---
discussion_number: 9505
title: "Code Smell: Using `repr` in programmatically significant ways"
author: schrockn
created_at: 2024-04-29T21:12:08Z
updated_at: 2024-04-30T14:24:09Z
url: https://github.com/dagster-io/internal/discussions/9505
category: Python Code Smells and Anti-Patterns
---

## Do not use `repr` in programmatically significant ways

Python has a useful built-in function called [`repr`](https://docs.python.org/3/library/functions.html#repr) that returns a printable representation of an object. Users can overload this behavior by implementing the `__repr__` method on class.

This is very convenient for use in the python REPL, for logging, and in error messages. By convention the results of `repr` can themselves be evaluted as Python, but that is not formally enforced.

However this should not be used in programmatically significant ways, such as sorting, a hash function, or a key to look up in a dictionary. `__hash__` and `__eq__` already exist for providing value semantics for objects so they are can used in sets and as dictionary keys. Comparison functions should be more precise than comparing printable representations.

By using `repr` in a meaningful way, you risk a engineer editting the class, not updating the `repr` function, and introducing difficult-to-diagnore [bugs](https://github.com/dagster-io/dagster/pull/21497).