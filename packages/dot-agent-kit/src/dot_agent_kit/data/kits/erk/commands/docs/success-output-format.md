## Execution Commands

**Submit to Erk Queue:**

```
erk submit {issue_number}
```

**Local Execution**

**Standard mode (interactive):**

```
erk implement {issue_number}
```

**Yolo mode (fully automated, skips confirmation):**

```
erk implement {issue_number} --yolo
```

**Dangerous mode (auto-submit PR after implementation):**

```
erk implement {issue_number} --dangerous
```
