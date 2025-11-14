---
discussion_number: 9682
title: "Code Smell: Callsites with multiple non-obvious positional parameters"
author: schrockn
created_at: 2024-05-10T11:25:12Z
updated_at: 2024-05-10T11:26:26Z
url: https://github.com/dagster-io/internal/discussions/9682
category: Python Code Smells and Anti-Patterns
---

## Use keyword arguments where the meaning of positional arguments is not obvious

How many time have you run into code that looks like this and been confused:

```python
some_random_function(None, False, True)
```

This code is difficult to reason about and is not self-documenting. Invariably you have to jump to the function definition and gather a bunch of context on the function. This is a lot of cognitive load.

```python
some_random_functon(optional_list=None, sort=False, coerce_to_ints=True)
```

This is much better.

A good rule of thumb is that if it is obvious from the name and the argument values what the operation does, feel free to use positional arguements.

Here's an example where keyword arguments would be annoying and gross:

```python
number = add(some_number, return_value_from_other_func)
```

You do not need to understand the argument names to understand their behavior here. All the credible options (`n1` and `n2`; `left`and`right`) add no useful information or value, only noise.

### Python can help us out a lot: required keyword arguments

Python has a nice [feature](https://peps.python.org/pep-3102/) where a function/method can _require_ that its callers use keyword arguments.

In addition to making callsites more clear, keyword-only arguments can also be reordered without breaking callers, which is great.

That means you can always make keyword-only arguments positional later, but changing a positional argument to keyword-only argument is breaking.

Therefore, when in doubt, _make the argument keyword-only_. It is a so-called "two-way door". We can always make arguments positional later as a non-breaking change.

