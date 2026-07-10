# BRIEF — dev-4 — Harden the auto-merge actuator's arming guard (pre-arming safety)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. This hardens the exact control the Operator is about to ARM — fail-safe is paramount.

## Why
Independent review of the actuator (validators/creator_engine_validator/forge/automerge_actuator.py) found two pre-existing safety smells that must be hardened BEFORE the Operator flips run_mode to arm auto-merge:
1. The dormancy guard is `if run_mode == "dev": return Dormant` — a NON-strict check. Any non-"dev" string (a typo like "Dev", a stray/unknown value) would pass and ARM the actuator. An arming control must fail-closed by ALLOWLIST.
2. The actuator reads `run_mode` from the decision JSON ARTIFACT, not from live `.ce/state/automerge/policy.json` at actuation time. So if armed ("ceo"), decisions emitted, then reverted to "dev", the already-emitted "ceo" artifacts would STILL actuate. Disarming must be immediate.

## Branch
`ce-harden-actuator-arming-guard` off CURRENT origin/main (git fetch origin main first — #642 just merged, the actuator + caller are now in main). Fresh worktree.

## Scope (study first: automerge_actuator.py actuate_if_ready, especially the run_mode dormancy guard ~lines 64-65; automerge_policy.py for the live-state loader e.g. load_automerge_policy_state / automerge_policy_state_path)
1. STRICT ALLOWLIST: define `_ARMING_RUN_MODES = frozenset({"ceo"})` (the ratified auto-merge arming value). The actuator actuates ONLY if the effective run_mode is in `_ARMING_RUN_MODES`; EVERYTHING else — "dev", unknown strings, empty, None, whitespace, case-variants like "Dev"/"CEO" — returns Dormant (reason e.g. "run_mode_not_armed"), fail-closed. (Decide whether "ceo" is case-sensitive exact-match — recommend exact lowercase only; document it.)
2. LIVE RE-VERIFY: at actuation time, ALSO load the live `.ce/state/automerge/policy.json` run_mode (via the existing automerge_policy loader) and require IT to be in `_ARMING_RUN_MODES` too — do NOT trust only the decision artifact's run_mode. If the live policy.json run_mode is not armed (e.g. reverted to "dev"), return Dormant even if a stale artifact says "ceo". This makes disarm immediate. If policy.json is missing/unreadable → Dormant fail-closed (do NOT actuate).
   (Preserve all the OTHER existing predicates — kill_switch, class_flag, enabling_decision_ref, required_checks-green — unchanged. This change only tightens the run_mode gate + adds the live re-verify.)

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/forge/automerge_actuator.py`
- `validators/tests/unit/test_automerge_actuator.py` (extend) and/or `test_automerge_policy.py` if the caller tests live there — match where the existing actuator tests are
- `.ce/changelog/ce-harden-actuator-arming-guard.md`, `.ce/pr-manifests/ce-harden-actuator-arming-guard.md`
Do NOT touch the workflow, the caller cli, ce_cli, or policy.json itself (you ARM nothing — you only harden the guard).

## Tests
- run_mode "dev" → Dormant; unknown/"Dev"/"CEO"/""/None/whitespace → Dormant (parametrized); "ceo" + all other predicates green → actuates (mock gh_runner).
- LIVE re-verify: decision artifact says "ceo" but live policy.json says "dev" → Dormant (no actuation). policy.json missing → Dormant.
- No existing predicate test weakened.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-harden-actuator-arming-guard`
- Carriers via carrier_gen (dashed slug); single carrier; manifest `- **Declared work class:** story`.
- STOP and emit: `READY-FOR-HARVEST: branch ce-harden-actuator-arming-guard, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- You ARM nothing (no policy.json edits, no run_mode flip). Stay in allowed paths. No push.
