# SEED BRIEF — dev-4 — ce-ops#382 brain-drift false-RED on persistent checkout

Role: implementer. Branch: `ce-382-brain-drift-local-reconcile` (off fresh
origin/main). Contained DGX seat — controller harvests (you commit + signal
READY-FOR-HARVEST with SHA; self-push may be unavailable, that's fine).

## Problem (bit the FIRST external contributor today — pitch-critical)
`ce validate-pr` gives a FALSE-RED locally on a persistent checkout: the
brain-drift gate (`brain verify --drift --state-root .ce/state`) fails on
divergence between the tracked canonical `.ce/brain/assertions.yaml` and the
gitignored instance-local `.ce/state/brain/assertions.yaml`. CI is GREEN because
a fresh checkout has NO `.ce/state/brain/`, so nothing diverges. After
state-changing PRs (e.g. #686 work-class rename) local state drifts and the gate
fails even though the contributor's diff is clean and touches nothing brain-
related. The error points at a gitignored file contributors are told never to
edit → inscrutable, un-fixable within PR scope, and it makes the local preflight
untrustworthy.

## Relevant code (locate + confirm before changing)
- `validators/creator_engine_validator/checks/ce_brain_drift.py` (the drift gate)
- `validators/creator_engine_validator/pr_preflight.py` (invokes the gate in the
  local suite)
- `validators/creator_engine_validator/brain_runtime.py`,
  `checks/ce_brain_assertions.py`, `brain_bootstrap.py`, `ce_cli.py` (brain CLI)
- CI reference: `.github/workflows/validate.yml` (confirm how/whether it runs the
  drift gate in a fresh checkout — the fix must make local posture MATCH CI).

## Fix (implement all three; keep the gate's real signal intact)
1. **Local run mirrors CI posture** — when instance-local `.ce/state/brain/`
   diverges from canonical purely as instance-local runtime drift (NOT a change
   the contributor made to the tracked canonical `.ce/brain/` files), the local
   `validate-pr` brain-drift gate must NOT fail the run. Prefer AUTO-RECONCILE
   local instance-state from canonical before gating (so the gate still runs and
   still catches real canonical-vs-runtime contract violations) over blanket
   skip. Do NOT weaken the gate's ability to catch a genuine drift the
   contributor introduced by editing tracked `.ce/brain/` sources — distinguish
   "instance-local runtime drift" (ignore/reconcile) from "diff touches tracked
   brain sources" (still gate).
2. **One-command reconcile** — add `ce brain sync` (or `reconcile`) that resets
   local instance-state from canonical sources deterministically. Wire it into
   the brain CLI group. Idempotent; clear success output.
3. **Actionable message** — if any drift-related condition still surfaces, the
   error must say: it's instance-local (not a problem with their change), name
   the exact reconcile command to run, and that CI is unaffected. No bare FAIL.

## Constraints
- TERRITORY: validators/** (brain + preflight + tests) only. Do NOT touch
  conveyor files (frozen pending ce-ops#388), the forge triage modules
  (dev-1 has #376 there), or checks/fleet_manifest_guard.py (dev-1 has #369).
  A troubleshooting line in docs/guide/contributing-to-ce.md is OPTIONAL and
  allowed (no open PR touches it) — add only if it reads cleanly; ZERO ce-ops#
  refs in any docs/** file.
- Tests REQUIRED (test-coupling gate): cover (a) instance-local drift →
  reconciled/non-gating locally, (b) a genuine canonical-source change in the
  diff → still gates, (c) `ce brain sync` idempotent reconcile. Assert the
  actionable message content.
- FULL `ce validate-pr` GREEN in ONE pass before signal. Worktree source,
  PYTHONPATH=validators; `rm -rf validators/build validators/*.egg-info` first.
- PR hygiene: `.ce/changelog/ce-382-brain-drift-local-reconcile.md` + carrier
  via carrier_gen `write_carriers(base=<merge-base>)` (never hand-edit; stem ==
  branch slug). New `ce brain sync` subcommand may trip test_v1_docs_reconciliation
  / CLI-reference — if so, run `gen_cli_reference --write` and update README if
  the reconciliation test requires it.
- PR body: exactly one `- **Declared work class:** <XS|S|M|L>` (size honestly;
  likely M given new subcommand + gate logic + tests).

## REPORT
Branch, committed head SHA (+ READY-FOR-HARVEST or self-push result), preflight
one-pass result, the three tests + fail-without/pass-with, the reconcile command
name, any docs-reconciliation coupling you had to satisfy, anomalies. STOP after
push/signal — do NOT approve/merge.
