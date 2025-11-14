---
discussion_number: 9602
title: "Code smell: Errors too deep in the call stack or too far into the program"
author: schrockn
created_at: 2024-05-06T11:43:07Z
updated_at: 2024-05-06T11:44:09Z
url: https://github.com/dagster-io/internal/discussions/9602
category: Python Code Smells and Anti-Patterns
---

# Catch errors as early as possible and use runtime invariants to do it

There is little more frustrating than consuming Python code that will accept incorrect parameters and only surface errors deep in the call stack in a place not obviously connected to the location of the mistake. You are left to guess and check or even debug the library you are consuming.

The solution is explicit check for invariant violations or errors as early as possible, and provide context in the error message.

Dagster has the `check` module to do this conveniently. Imagine we had the following program.

```python=
class Wrapper:
    def __init__(self, value):
        self.value = value

    def add_one(self):
        return self.value + 1


def a_func(an_int) -> None:
    wrapper = Wrapper(an_int)
    wrapper.add_one()

a_func("1")
```

This results in the following error:

```
> python test.py
Traceback (most recent call last):
  File "/Users/schrockn/code/dagster-io/dagster/test.py", line 16, in <module>
    a_func("1")
  File "/Users/schrockn/code/dagster-io/dagster/test.py", line 14, in a_func
    wrapper.add_one()
  File "/Users/schrockn/code/dagster-io/dagster/test.py", line 9, in add_one
    return self.value + 1
TypeError: can only concatenate str (not "int") to str

```

In order to debug this you have to inspect the code and understand the state of process when the error was thrown.

Now instead let's add a check:

```python
from dagster import _check as check

def a_func(an_int) -> None:
    check.int_param(an_int, "an_int")
    wrapper = Wrapper(an_int)
    wrapper.add_one()
```

When running this program you get the following error:

```
> python test.py
Traceback (most recent call last):
  File "/Users/schrockn/code/dagster-io/dagster/test.py", line 6, in <module>
    a_func("1")
  File "/Users/schrockn/code/dagster-io/dagster/test.py", line 4, in a_func
    an_int = check.int_param(an_int, "an_int")
  File "/Users/schrockn/code/dagster-io/dagster/python_modules/dagster/dagster/_check/__init__.py", line 547, in int_param
    raise _param_type_mismatch_exception(obj, int, param_name, additional_message)
dagster._check.ParameterCheckError: Param "an_int" is not a int. Got '1' which is type <class 'str'>.
```

This is obvious and easy to fix. You can assess the error and craft a resolution by inspecting the call stack alone. You don't need to understand the entire program.

If you do not catch errors early, bug investigations and resolution are much more likely to be:

- Dependent on the state of the process
- Far away, both temporally and physically, from the actual source of the error.
- Non-deterministic

Fixing error with the above characteristics are often orders of magnitude more expensive than errors that are function of localized code.

## Case Study: check calls at every public API entry point

Why do we put `check` calls at every public API entry point? After all we have type hints. Isn't this unnecessary boilerplate and runtime overhead?

The reasons:

1. While we use typehinting in our code base and catch typing errors in CI, not all of our users do. Therefore we cannot trust anything passed in our system to actually abide our type checks.
2. If we let values into the system that violate type checks, it will "infect" the whole system. We would encounter issues all the time where unmodified user-provided values make it appear that the type system is lying. That would cause systematic distrust in the type system throughout the entire codebase.
3. Errors are clearly communicated to users. This is a better user experience and reduces our support burden. Imagine a world where users continually reported inscrutable errors deep in our callstack. It would be a nightmare.

That is why a class like `AssetSpec` has a `__new__` function like so:

```python
    def __new__(
    cls,
    key: CoercibleToAssetKey,
    *,
    deps: Optional[Iterable["CoercibleToAssetDep"]] = None,
    description: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    skippable: bool = False,
    group_name: Optional[str] = None,
    code_version: Optional[str] = None,
    freshness_policy: Optional[FreshnessPolicy] = None,
    auto_materialize_policy: Optional[AutoMaterializePolicy] = None,
    owners: Optional[Sequence[str]] = None,
    tags: Optional[Mapping[str, str]] = None,
):
    from dagster._core.definitions.asset_dep import coerce_to_deps_and_check_duplicates

    key = AssetKey.from_coercible(key)
    asset_deps = coerce_to_deps_and_check_duplicates(deps, key)

    return super().__new__(
        cls,
        key=key,
        deps=asset_deps,
        description=check.opt_str_param(description, "description"),
        metadata=check.opt_mapping_param(metadata, "metadata", key_type=str),
        skippable=check.bool_param(skippable, "skippable"),
        group_name=check.opt_str_param(group_name, "group_name"),
        code_version=check.opt_str_param(code_version, "code_version"),
        freshness_policy=check.opt_inst_param(
            freshness_policy,
            "freshness_policy",
            FreshnessPolicy,
        ),
        auto_materialize_policy=check.opt_inst_param(
            auto_materialize_policy,
            "auto_materialize_policy",
            AutoMaterializePolicy,
        ),
        owners=check.opt_sequence_param(owners, "owners", of_type=str),
        tags=validate_tags_strict(tags),
    )
```

While annoying to write initially catching errors early and with obvious error messages saves us enormous pain later.

Note: A good project would be to make this less boilerplate-y and then write lint rules to make sure that _all_ of our public APIs do runtime parameter checking. We are quite inconsitent at the moment, which is understandable, given that it is somewhat annoying to write all of these checks.
