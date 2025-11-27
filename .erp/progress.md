---
completed_steps: 0
total_steps: 4
---

# Progress Tracking

- [ ] 1. **Consistency**: Same file already uses `Ensure.invariant()` (line 24-27), `Ensure.truthy()` (line 191-194), and `Ensure.path_exists()` (line 146)
- [ ] 2. **Minimal change**: Single function, straightforward replacement
- [ ] 3. **Import already present**: `from erk.cli.ensure import Ensure` is on line 10
- [ ] 4. **Same error behavior**: `Ensure.invariant()` outputs "Error: " prefix in red and raises `SystemExit(1)`
