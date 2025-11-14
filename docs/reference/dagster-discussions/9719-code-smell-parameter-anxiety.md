---
discussion_number: 9719
title: "Code Smell: Parameter Anxiety"
author: schrockn
created_at: 2024-05-14T11:21:18Z
updated_at: 2024-05-16T17:44:46Z
url: https://github.com/dagster-io/internal/discussions/9719
category: Python Code Smells and Anti-Patterns
---

## Functions should not have too many parameters that impact behavior and control flow.

When programming you consume functions some time that have a ton of parameters and you are overwhelmed by the options. How do all the combinations work? If I set some flag and some other flag, how do they interact?

The feeling you are experiencing is **parameter anxiety**. From from irrational, this reaction is often proper and appropriate. Is your intuition accurately telling you that something has gone off the rails. Tl;dr: It smells.

### Not all parameters are the same

This doesn't happen _every_ time. For example, there are perfectly valid reasons to have a database row with a ton of columns. A data class that backs each row will have a lot of properties. When you interact that class you don't feel anxiety.

The reason is that these parameters do not impact behavior or control flow, and therefore to do not meaningfully contribute to the complexity of the program in that context.

A good heuristic of determining if a function parameter behaviorial or not is whether or not its inclusion increases the [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) of said function. Cyclomatic complexity measures the number possible paths code can take through a particular unit of code.

Here's an example from our code base:

```python
def get_prev_partition_window(
    self, start_dt: datetime, respect_bounds: bool = True
) -> Optional[TimeWindow]:
    # a bunch of code
    if respect_bounds: ...
        # more code

    return prev_window
```

I've commented everything out except the only `if` statement in this function for clarity. As you can see the cyclomatic complexity increased by one when `respect_bounds` was added, since there are two "paths" execution can go through.

This can quickly spin out of control. Let's restrict our analysis to required boolean arguments for the sake of simplicity. With every additional boolean argument, it's likely that the cyclomatic complexity is on the order of `O(2^N)` of the number of parameters. It grows expotentially.

We can explain this with code. In the following contrived function we can build binary representation from "000" to "111" using three booleans. This shows there are eight possible code paths. The number of code paths is `2^3` which is `8`.

```python

def build_binary_rep(option_one: bool, option_two: bool, option_three) -> str:
    binary_rep = ''
    if option_one:
        binary_rep += "0"
    else:
        binary_rep += "1"

    if option_two:
        binary_rep += "0"
    else:
        binary_rep += "1"        ...

    if option_three:
        binary_rep += "0"
    else:
        binary_rep += "1"

    return binary_rep
```

This explicit property explains your instinctive parameter anxiety. It's quite rational, as multiple behavioral parameters spin out of control.

### Alternative approach: Composition and pushing complexity to call sites

An alternative approach is to decompose logic into functions and force callsites to put together their logic.

Here's a simple example:

```python
# Someone added capitalize because they thought it was convenient
def process_string(value: str, capitalize: bool = False):
    if capitalize:
        value = value.capitalize()
    call_other_function(value)

# callsite 1
process_string(s1)

# callsite 2
process_string(s2, capitalize=True)
```

Solving this by composition means eliminating the bool and pushing the `capitalize calls` to callsites

```python

# callsite 1
call_other_function(s1)

# callsite 2
call_other_function(s2.capitalize())
```

We have eliminated a function with a cyclomatic complexity of one, at the expense of forcing users to know about the `capitalize` method of `str`.

There are real tradeoffs here. Too much composition can cause more complexity than a boolean parameter, and there is a judgement here. In example above regarding capitalization it is fairly obvious that this is the right move, since `capitalize` is a built-in. In other cases it is not so obvious (importing a new symbol is a real cost, for example).

Keep the exponential growth with respect to the number of parameters in mind. The more parameters, the more likely it is worth it to expel a parameter from a function, because of this exponential effect.

And this is case where there is no silver bullet. There are no solutions, only tradeoffs. The behavioral parameter represents some level of essential complexity in the software. If you cannot eliminate that essential complexity, you have to manage it. It's your judgement as an engineer as to how you organize the complexity.
