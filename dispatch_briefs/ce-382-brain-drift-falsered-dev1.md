# SEED BRIEF — ce-ops#382: fix validate-pr brain-drift false-RED — SEAT: dev-1

**Context:** `ce brain verify --drift --state-root .ce/state` (CI step in validate.yml + local `ce validate-pr`) FALSE-FAILS on a persistent checkout. Root cause: `.ce/state/brain/assertions.yaml` is **instance-local, gitignored, rebuildable** state; CI runs in a FRESH checkout where it's ABSENT → passes; a persistent local checkout accumulates a copy that DIVERGES from the tracked canonical `.ce/brain/assertions.yaml` (e.g. after #686 updated canonical) → the drift check FAILS on a file the contributor is told never to touch and can't fix within their PR scope. Live incident 2026-07-01 (blocked the contributing-guide PR; blocks Nitzan's onboarding).

**Branch:** `ce-382-brain-drift-falsered` (off `origin/main`). **Role:** implementer. **Work class:** by floor.
**Repo:** creator-engine/creator-engine. Non-contained: self-push + open PR.

## Goal — make the drift check behave the same locally as in CI
The drift check must NOT false-RED on a stale instance-local `.ce/state/brain/` that diverges from canonical. Pick the cleanest fix (your judgment, but keep the REAL drift protection intact):
- Option A (preferred if clean): the drift check reconciles/derives the comparison from CANONICAL `.ce/brain/` and treats a missing-or-stale instance-local `.ce/state/brain/` as "no drift" (mirroring CI's fresh-checkout condition) — i.e. instance-local staleness is not a failure, only a genuine divergence between the DELIBERATE tracked artifacts is.
- Option B: provide a documented one-command reconcile (`ce brain sync` or similar: rewrite `.ce/state/brain/assertions.yaml` from canonical) AND make validate-pr auto-reconcile-or-skip so the local run matches CI. Reference it in the contributing guide troubleshooting.
- At MINIMUM: replace the bare drift FAIL with an actionable message ("stale local brain state — run X; this is not a problem with your change") — but prefer actually not-failing.

The REAL invariant to preserve: a genuine divergence in the TRACKED canonical brain artifacts (the thing CI catches on a fresh checkout) must still fail. Only the instance-local-staleness false-positive is removed.

## Scope — keep tight (avoid pr_preflight.py; a parallel lane owns it)
- `validators/creator_engine_validator/checks/ce_brain_drift.py` (the drift-check logic) + its test `validators/tests/unit/test_ce_brain_drift.py`
- IF (and only if) the fix genuinely needs the CLI/validate-pr invocation layer, FLAG IT in your report and STOP before editing `pr_preflight.py` (a parallel lane #373 owns it) — we'll coordinate. Prefer solving it inside ce_brain_drift.py.
- Contributing-guide troubleshooting note (docs/guide/contributing-to-ce.md) ONLY if Option B; keep it minimal + sync the .html sibling.
- `.ce/pr-manifests/ce-382-brain-drift-falsered.md` + `.ce/changelog/ce-382-brain-drift-falsered.md`

## Evidence / DoD
- FULL `ce validate-pr` GREEN one pass (TMPDIR=/var/tmp PYTHONPATH=validators). Demonstrate: a deliberately-staled `.ce/state/brain/assertions.yaml` no longer false-fails, AND a genuine canonical divergence STILL fails (both in tests).
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; push; open PR w/ declared-work-class line. Do NOT approve/merge.
