---
completed_steps: 0
total_steps: 8
---

# Progress Tracking

- [ ] 1. Replace the manual `if not progress_file.exists()` block with `Ensure.path_exists(ctx, progress_file, f"Progress file not found: {progress_file}")`
- [ ] 2. Remove the now-unused `ProgressError` dataclass import and definition (if it's only used for this error case)
- [ ] 3. Remove the `json` and `asdict` imports if they're only used for this error case
- [ ] 4. Note: Success responses will remain as JSON with `ProgressSuccess` dataclass (per clarification)
- [ ] 1. This is incremental standardization - part of broader Ensure migration (1e241317)
- [ ] 2. Exit code changes from 0 to 1, which is a breaking change for callers using `|| true` pattern
- [ ] 3. Partial JSON → styled text conversion may create output format inconsistency
- [ ] 4. Must verify no external dependencies on ProgressError/ProgressSuccess dataclasses before removal
