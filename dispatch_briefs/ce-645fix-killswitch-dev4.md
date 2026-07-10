# BRIEF — dev-4 — #645 follow-up: live kill_switch re-verify (pre-arming fail-safe)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Amend your EXISTING branch `ce-harden-actuator-arming-guard`, drive back to READY-FOR-HARVEST GREEN.

## Why (independent review BLOCKER)
Your hardening correctly re-verifies live `run_mode` at actuation, but does NOT re-verify the live `kill_switch`. The live policy state object is loaded and its `.kill_switch` is read into memory then ignored. Failure case the actuator MUST refuse:
1. Policy run_mode="ceo", kill_switch=False → decision artifact emitted (artifact kill_switch=False).
2. Operator flips `kill_switch=true` in live `.ce/state/automerge/policy.json` as an EMERGENCY STOP.
3. Actuator runs: artifact-side kill_switch guard passes (artifact had False); live run_mode="ceo" passes; **live kill_switch is never checked** → auto-merge proceeds. The emergency kill switch is defeated for already-emitted decisions.

The kill_switch must work as a live emergency interrupt. This control is about to be ARMED — it must fail-closed.

## The fix (exactly this, minimal)
In `validators/creator_engine_validator/forge/automerge_actuator.py`, in `actuate_if_ready`, immediately AFTER the live `run_mode` armed check (currently ~line 96-97, `if not _run_mode_armed(live_policy.run_mode): return _dormant("live_run_mode_not_armed")`) add a live kill_switch guard:

```python
    if live_policy.kill_switch:
        return _refuse("live_kill_switch_active")
```

Use `_refuse` (not `_dormant`) — an active kill switch is an explicit refusal, mirroring the artifact-side guard at line 73. Keep the live-policy read you already added; just also honor its kill_switch.

## Tests (add to test_automerge_actuator.py)
Add a test asserting: decision artifact run_mode="ceo", kill_switch=False, BUT live policy.json has kill_switch=True → result is **Refused**, reason=`"live_kill_switch_active"`, `acted=False`, and **no gh calls** (`gh.calls == []`). Mirror the existing `test_stale_decision_armed_but_live_policy_dev_goes_dormant` setup (test_automerge_actuator.py ~line 231) but vary kill_switch instead of run_mode.

## Scope (do NOT exceed)
Allowed paths: `validators/creator_engine_validator/forge/automerge_actuator.py`, `validators/tests/unit/test_automerge_actuator.py`, and regen the two carriers (`.ce/changelog/ce-harden-actuator-arming-guard.md`, `.ce/pr-manifests/ce-harden-actuator-arming-guard.md`) if the diff line counts shift. NOTHING else (no policy.json, no .ce/state, no workflows, no ce_cli.py).

## Evidence to emit on READY
`rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-harden-actuator-arming-guard` GREEN, the new test name, and `commit && echo <SHA>`. Do not push.
