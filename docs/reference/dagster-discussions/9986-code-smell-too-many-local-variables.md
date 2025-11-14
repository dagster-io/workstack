---
discussion_number: 9986
title: "Code Smell: Too many local variables"
author: schrockn
created_at: 2024-06-03T10:33:35Z
updated_at: 2024-06-03T15:04:30Z
url: https://github.com/dagster-io/internal/discussions/9986
category: Python Code Smells and Anti-Patterns
---

## Do not let functions grow the point where they have too many local parameters

We subdivide and decompose our programs into functions. Deciding the right way to do this and at what granularity is one of the most essential things we do in programming to control complexity.

It is often said that you should divide your program into lots of little functions. While this is usually _more_ correct than having huge functions, it is not a hard and fast rule. Sometimes codebase suffers from the "Too Many Little Functions" (TBD) smell and impacts readability.

However, there are certain heuristics that indicate that things have "gone off the rails". One of those is too many local parameters.

Local parameters are more problematic in Python than in other programming languages, as their rules are less strict.

- Variables are not declared up front.
- Python code can reference variables that have not been assigned yet, and only report errors at runtime.
- Python variables shadow variables in their parent scope

These rules can both cause strange behavior but also limit how much work tooling can do over on your behalf:

Take this code:

```python
def foo() -> int:
    bar = {"val": 1}
    def baz() -> int:
        bar["val"] = 2
        return bar["val"]

    print(f"before: {bar['val']}")
    return_value = baz()
    print(f"after: {bar['val']}")
    return return_value

foo()
```

Since the dictionary here has reference semantics the call to `baz` mutates `bar`:

```
> python example.py
before: 1
after: 2
```

Now this might seem trivial because this code is simple and short. But imagine large inner functions placed within very large outer functions, and this gets problematic quickly. We have many such examples in our codebase.

Code with too many local variables always tends to become more complex and difficult to understand, as there is too much state and too many downstream consequences within one scope. Mutating one variable can cause a bug by impacting the value of another variable in a non-obvious way. Engineers also get naming fatigue as obvious variable names get "taken" within the scope, tempting people to just add an underscore or an alternative spelling, compounding the problem.

### Case study `multi_asset`

What inspired this code smell was the state of `multi_asset` at the [time](https://github.com/dagster-io/dagster/blob/3e4af271159587fa912f6a73fabeb06bb6f70bf3/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L519) of this article.

It had over 200 lines of non-commented code, 37 local variables, 17 of which were in a large inner function dynamically declared in scope.

![Screenshot 2024-06-02 at 4 49 15 PM](https://github.com/dagster-io/internal/assets/28738937/b77fcad4-0727-47e5-b8a8-a31086a85470)

This was not the only sin of this region of code. The entire decorator-to-AssetsDefinition creation machinery at the time of this writing was a rat's next of complexity and a technical liability, an example of Systemic Code Duplication (yet to be written), [Parameter Anxiety](https://github.com/dagster-io/internal/discussions/9719), and other smells.

### Tactics for resolving

The most natural and obvious thing to do is the decompose the large function into lots of smaller ones. However, that often is itself too difficult, as the functions has grown too large and too interconnected.

It is also often tempting to just make the function an object and make all local variables instance variables of an object. While this can have incremental benefits, it can also lead to its own problem. You have effectively just moved the problem from being an overcomplicatedd function to being an overcomplicated class.

One tactic that can be effective is to systematically move the structure of the function to an immutable value object with caching, read-only parameters.

```python
def really_long_function_that_does_foo():
    var_one = get_one()
    ### ... lots of code
    var_two = get_two()
    ### ... lots of code
    var_three = combine(var_one, var_two)
```

There is actually a tight function here, but it can be hard to see in a very long function. (Imagine `really_long_function_that_does_foo` was hundreds of line long.)

Extracting out a class with properties can start to tease apart, apply typing, and formally encode the implicit DAG of local variables.

```python
class FooState:
    @cached_property
    def var_one(self) -> TypeOne:
        return get_one()

    @cached_property
    def var_two(self) -> TypeTwo:
        return get_two()

    @cached_property
    def var_three(self) -> TypeThree
        return combine(self.var_one, self.var_two)
```

The cached DAG of state object allows the engineer to incrementally provide a structure that ends up documenting and formalizing the complex dependency graph of computation in a huge function without introducing a huge performance penalty.

This tactic was used to break apart `multi_asset`, in a stack culminating with this [PR](https://github.com/dagster-io/dagster/pull/22230).
