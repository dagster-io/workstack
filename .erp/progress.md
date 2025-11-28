---
completed_steps: 0
total_steps: 37
---

# Progress Tracking

- [ ] 1. --session-id CLI argument
- [ ] 2. SESSION_CONTEXT environment variable (format: "session_id=<uuid>" OR bare UUID)
- [ ] 3. Error if neither available
- [ ] 1. **No session ID available**
- [ ] 2. **Session file not found**
- [ ] 3. **Malformed JSONL**
- [ ] 4. **No plan found**
- [ ] 5. **Plan file deleted**
- [ ] 6. **Multiple plans found**
- [ ] 1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/session_get_plan.py`
- [ ] 2. `packages/dot-agent-kit/tests/unit/kits/erk/test_session_get_plan.py`
- [ ] 3. `packages/dot-agent-kit/tests/integration/kits/erk/test_session_get_plan_integration.py`
- [ ] 1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`
- [ ] 1. ✓ Session ID resolution (CLI arg or env var)
- [ ] 2. ✓ Session file discovery across all projects
- [ ] 3. ✓ Malformed JSON handling (skip invalid lines)
- [ ] 4. ✓ Plan filename extraction (main file, not agent logs)
- [ ] 5. ✓ Plan file verification (warning if deleted)
- [ ] 6. ✓ Multiple plans handling (return most recent)
- [ ] 7. ✓ Structured JSON output (success/error)
- [ ] 8. ✓ Text output mode for scripting
- [ ] 9. ✓ Helpful error messages with context
- [ ] 10. ✓ Full test coverage (unit + integration)
- [ ] 11. ✓ LBYL pattern compliance
- [ ] 12. ✓ Type hints throughout
- [ ] 1. **Create command skeleton** (30 min)
- [ ] 2. **Implement session ID resolution** (20 min)
- [ ] 3. **Implement session file discovery** (30 min)
- [ ] 4. **Implement plan extraction** (45 min)
- [ ] 5. **Implement output formatting** (20 min)
- [ ] 6. **Write unit tests** (1.5 hours)
- [ ] 7. **Write integration tests** (45 min)
- [ ] 8. **Update kit.yaml** (5 min)
- [ ] 9. **Manual testing** (30 min)
- [ ] 1. **Extract shared utilities** to `session_utils.py`:
- [ ] 2. **Create query-specific commands**:
- [ ] 3. **Consider framework** if 3+ queries exist:
