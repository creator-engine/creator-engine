# ce244 CORRECTION 1 — #609 review found one blocking gap + cheap hardening (within existing 5 paths)

Independent review (ce-dev-2) on #609 = REQUEST_CHANGES, one BLOCKING item. Fix all of the below on branch `ce244-bootstrap-ssot-overlay`, re-run full `ce validate-pr` GREEN, push (new head), report READY-FOR-HARVEST. NO new paths — everything is within your existing 5 allowed paths (ssot json + generator + test + carriers).

## 1. BLOCKING — test gap: AGENTS.md live-path refusal
`validators/tests/unit/test_gen_controller_bootstrap.py::test_generator_refuses_live_paths` asserts refusal for `CLAUDE.md`, `.claude/agents`, and repo-root, but NOT `AGENTS.md`. The generator already refuses `AGENTS.md` (it's in `LIVE_ROOT_FILES`); the TEST must assert it too (AGENTS.md is a design-enumerated live bootstrap path). Add:
```python
with pytest.raises(SystemExit):
    ensure_safe_out_dir(REPO_ROOT / "AGENTS.md")
```
(match the existing assertion style in that test).

## 2. CONTENT — subagent_model_routing must encode the Claude-SUBAGENT tiers explicitly
The overlay's `controller_knowledge_overlay.subagent_model_routing` must make the Claude-subagent routing unambiguous (this is the high-frequency discipline the overlay exists to enforce). Ensure these keys/values are present (ADD any missing; keep existing codex-seat entries):
- `"claude_subagent_mechanical"`: `"Haiku — fleet_recon / ops_triage / liveness / verification"`
- `"claude_subagent_substantive"`: `"Sonnet — architect_research / implementer / reviewer / harvest_intake"`
- `"claude_subagent_controller_only"`: `"Opus — controller/main loop ONLY; NEVER a subagent"`
- `"forks"`: `"FORBIDDEN for execution — use restricted custom roles, never context-inheriting fork"`
Keep the existing codex routing (`codex_work_seat` high default, `codex_hardest` xhigh, Claude controllers effort:high). No drift-prone version strings (tier+effort labels only). If `validate_ssot` enumerates required sub-keys of `subagent_model_routing`, update it to require these; otherwise leave validation as-is (it only requires the mapping).

## 3. HARDENING — complete the fail-closed guarantee (cheap, same generator file)
- Add `"acceptance_safety_notes"` to `REQUIRED_SECTIONS` in `scripts/gen-controller-bootstrap.py` (it exists in the JSON but isn't required → silent-delete risk).
- In `validate_ssot()`, also validate `metadata["ratification_status"]` is present (the field is in the JSON + named in the design; currently unchecked).

## DoD / RULES
- Full `ce validate-pr --base origin/main --head-ref ce244-bootstrap-ssot-overlay` GREEN in ONE pass (use ce validate-pr, NOT raw pytest). The new test must pass; generator still refuses all live paths; rendering still deterministic.
- Diff stays within the existing 5 allowed paths (ssot json, generator, test, changelog, carrier). If the carrier path-set is unchanged, no carrier edit needed; if you touch a new file, STOP+report (you should not need to).
- PR body still carries exactly `- **Declared work class:** story`.
- A new push DISMISSES the prior review → that's expected; report READY-FOR-HARVEST and the new head SHA; controller re-reviews + gates. Do NOT push until GREEN; HOLD — no self-approve/merge/enqueue.
- If validate-pr is RED on any OTHER out-of-scope file → STOP + report.
