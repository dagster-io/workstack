---
discussion_number: 9753
title: "Code Smell: Using overly specific context objects in context-agnostic code paths"
author: schrockn
created_at: 2024-05-16T13:19:25Z
updated_at: 2024-05-16T13:19:25Z
url: https://github.com/dagster-io/internal/discussions/9753
category: Python Code Smells and Anti-Patterns
---

## Do not pass overspecified context objects to code that is otherwise generic and context-agnostic

We have a lot of context objects in the Dagster framework. (We have _too many_ of them in our public APIs, but that is a different subject.)

They serve a very useful purprose. They indicate where code is meant to be executed and provides an object to thread state that we know is available in that context. It is also a seam of testability, so the author can simulate environmental states.

```python
# `some_function` is called in the AssetDaemonContext. Good to know!
# We can also test lots of scenarios by creating AssetDaemonContext objects 
def some_function(context: AssetDaemonContext): ...
```

Context objects are very convenient, but they come at a price: they explictly couple the piece of code to a specific operating environment.

This causes a very practical problem if you want to repurpose code to execute elsewhere. You now have to remove the context from that codepath. That can be a lot of work, and engineers may have unnecessarily coupled some piece of code to that operating environment for no good reason.

The best practice is to stop using the context object as quickly as possible, and shuffle its constiuent properties into downstream code, and only the properties that that code actually needs. That makes it maximally reusable.

Consider:

```python
class SomeContext:
    num_one: int
    num_two: int

def some_entry_point(context: SomeContext):
    overly_specific_add(context)
    
# Overly specific. No reason to use context object
# Someone might add more state the context and some
# engineer might be tempted to use it, and now
# there is too much coupling
def overly_specific_add(context: SomeContext) -> int:
    return context.num_one + context.num_two
```

Instead imagine the ability to reuse a more generic function.

```python
def some_entry_point(context: SomeContext):
    overly_specific_add(context.num_one, context.num_two)
    
def generic_add(num_one: int, num_two: int) -> int:
    return num_one + num_two
```

This is a trivial example, but it does prove the point. `generic_add`
is much more reusable, and has a much clearer contract.

Here's an example PR [stack](https://github.com/dagster-io/dagster/pull/21897) that was required to move the evaluation of scheduling conditions out of the asset-daemon-specific context into a configuration that could be invocable by user in testing environments.

We had to do quite a bit of surgery to remove references to the `AssetDaemonContext` in that code and instead "hoist" the properties of the `AssetDaemonContext` to a more generic object.

### This is good advice from our users too

We pass a lot of specific context objects to users of our framework. We should be advising users to immediately pull only the objects they need off the context, and then pass those plain objects down to their business logic. This ends up with a much more nicely layered system where they have reduced their expose to Dagster's surface area in a good way and "control their own destiny."