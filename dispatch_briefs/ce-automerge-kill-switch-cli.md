# SEED BRIEF — `ce automerge-kill-switch` CLI (L2 auto-merge P1)

**Context:** L2 auto-merge is LIVE (docs-XS/S, ce-dev-2-approved only). Today the only
way to disarm is editing the GitHub Actions workflow env `CE_AUTOMERGE_KILL_SWITCH` — a
privileged, slow, error-prone path. The actuator ALSO honors a durable live-policy
kill-switch (`automerge_actuator._live_policy_state()` → `live_policy.kill_switch`;
refuses with `live_kill_switch_active` when set). Give operators a **one-command
governed kill-switch** over that live-policy state.

**Branch:** `ce-automerge-kill-switch-cli` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely S).
**Repo:** creator-engine/creator-engine.

## Goal
Add `ce automerge-kill-switch` with three actions:
- `ce automerge-kill-switch status` — print current live-policy kill-switch state (read-only).
- `ce automerge-kill-switch on` — set the live-policy kill-switch → auto-merge DISARMED.
- `ce automerge-kill-switch off` — clear it → auto-merge re-armed (only re-enables what
  policy already allows; does NOT bypass author≠approver, work-class, or CI gates).

Persist to the SAME durable store the actuator reads: `automerge_policy_state_path()` /
`load_automerge_policy_state()` in `forge/automerge_policy.py` (write a matching
save/update helper if none exists; keep the schema + `AutoMergePolicyStateError`
handling consistent). The `off` action must be a no-op-safe idempotent write; `on` must
fail CLOSED (if the state file can't be written, exit non-zero and print the manual
`CE_AUTOMERGE_KILL_SWITCH` fallback so the operator is never left thinking it's disarmed
when it isn't).

## Scope — exactly these paths
- `validators/creator_engine_validator/ce_cli.py` (register the subcommand next to
  `automerge-decide`/`automerge-status`/`automerge-actuate`; mirror their arg style + the
  help-text block at the top of the file).
- `validators/creator_engine_validator/forge/automerge_policy.py` (state read/write helper if needed).
- `validators/tests/unit/test_automerge_*.py` (add coverage: status reads, on sets +
  actuator then refuses `live_kill_switch_active`, off clears, write-failure fails closed).
- `.ce/pr-manifests/ce-automerge-kill-switch-cli.md` + `.ce/changelog/ce-automerge-kill-switch-cli.md`.

Do NOT touch the workflows, the actuator's refusal logic, or any other gate. Code-class
diff → the test-coupling gate requires new tests (you're adding them).

## Evidence / DoD
- `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp if host /tmp/.git trap).
- Demo transcript: `status` → `on` → actuator refuses `live_kill_switch_active` → `off` → actuator dormant/ready again.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; push; open PR with declared-work-class line in body. Do NOT approve/merge.
