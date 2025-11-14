---
discussion_number: 9791
title: "Code Smell: A God Class"
author: schrockn
created_at: 2024-05-20T10:26:24Z
updated_at: 2024-05-20T14:59:03Z
url: https://github.com/dagster-io/internal/discussions/9791
category: Python Code Smells and Anti-Patterns
---

## Do not let classes or functions grow to be too large and assume too many responsibilities

Classes and functions should not be too large or assume too many responsibilities. We know this, but we violate this rule sometimes. 

It is convenient to have a single object. You can pass it around. You can centralize a bunch of capabilites and when you press "dot" in your IDE all of them are right there. You only have to pass a single object to a class, and the entire system appears at your fingertips. You justify to it to yourself because at least you do not have global state.

But at some point it spins out of control. Engineers swoop in to add "just" one more feature, thinking, "Oh I'll refactor this at some point." Because it is so central, it is natural wedge to inject cross-cutting tooling and monitoring. It becomes a natural extension point because it is a point of leverage. It is passed everywhere, consumed by all, and understood by none.

You have built a God class (a.k.a [God object](https://en.wikipedia.org/wiki/God_object)). No single person understands it or claims to. Everyone fears to defy it and challenge it. It is all-knowing and in our daily lives.

God classes are extremely dangerous because they are so central to a system and so difficult to unwind. Engineers are always never incentived to fix them, and are almost always incentives to add to them, as it is the only way to add features. 

### `DagsterInstance` is the Emporer God King Class of Dagster

We have a God Class, and its name is `DagsterInstance`. It is a vengeful, dangerous God. Almost mockingly, it lives in an `__init__.py` file (a good smell candidate), is over 3200 lines, and has over 180 methods. Physical size is not its true problem though.

![Seems loving when there, vengeful when changed](https://github.com/dagster-io/internal/assets/28738937/4d875096-1beb-49e1-9476-dfcf335b0ab8)

_Loving when it works; Vengeful when it doesn't_

It has multiple overlapping properties that make it particularly difficult to change and manage. It is:

* The main interface to our metastore and event log, the most critical data structures in our product.
* The shim layer to call hosted commercial product
    * This violates ["Operations that mislead about their performance characteristics"](https://github.com/dagster-io/internal/discussions/9541)  and it presents as a class that accesses a local database, but can instead does API calls over the public Internet.
* Constructed and configured via a bespoke, problematic configuration system.
* Ubiquitous in our code base and public APIs.
* Subclassed by several classes across several GitHub repos.
* Depended on by external users for direct API access for critical, advanced use cases.

These properties complect and make `DagsterInstance` both highly resistant to change and dangerous to change. Bringing this under control will be an [architectural challenge](https://github.com/dagster-io/internal/discussions/9790) going forward.

### Mitigations

Taming the God class typically requires a two-prong approach. You must consider how to break up the implementation and how to subdivide and evolve the interface from the standpoint of callers. 

#### The God Class is unknowable

Once the system has a God class no one understands it. Many engineers have authored code within it, and it has no owner. Therefore is no single person that understands the interdependencies and implicit assumptions. Effectively the complexity is _unknowable_, which is one reason why the God Class is so dangerous. 

Frustratingly, this situation often defies upfront analysis. Instead it is only act of refactoring and re-architecturing itself that can begin to unveil the truth. Simply put, you just have to start doing stuff and seeing how it feels, what breaks, and what the consequences are. Defying the God Class is not for the feint of heart.

#### Decompose and subdivide: Just start to move shit around

Starting to break up and reorganize the implementation first is often easier because it is a "two way door." You are maintaining current contract of the class but incremental refactoring to make it more manageable. Breaking up the God class' single implementation file is often a great way to build momentum. Even this simple step can expose what the interdependencies.

The breaking up of an implementation can also yield insights about the what the top-level interface should become. If you can cleanly breakup the implementation, this means that can likely breakup the interface along similar lines, as your interfaces should reflect the underlying constraints of the implementation.

#### Or Categorize and Namespace: Just start wrapping

Sometimes breaking apart the class is prohibitively difficult, because the class is so intertwined and interdependent and it cannot be effectively broken up. This can mean that the contract the class claims to fulfill is deeply flawed, and only by changing it can you effectivtely start to break it apart.

The first step here is introduce higher level wrappers and hold an instance of the God object and begin to shift callsites to access the higher level wrappers. This typically is more thrashy and disruptive and it requires changing code in modules that depend on the God Class.
