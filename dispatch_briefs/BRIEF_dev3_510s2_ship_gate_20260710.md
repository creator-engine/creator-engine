# DISPATCH — dev-3 — 2026-07-10 — unit: ce-510 slice 2 — release-acceptance gate mechanics — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-510-ship-gate-s2 <full-40-hex-sha>`
or `BLOCKED ce-510-ship-gate-s2 <one-line-reason>`.
Branch `ce-510-ship-gate-s2` off freshly fetched origin/main; worktree /var/tmp/wt-ce-510-ship-gate-s2.
SUITE POLICY: focused tests only; commit before signal.

## Context (embedded)
The release-acceptance stage DESIGN just merged: `docs/design/release-acceptance-stage.md`
(read it FIRST — it is your spec). Slice 1 of the rehearsal harness is shipped under
deploy/rehearsal/ (evidence-format schema_version 1). This slice builds the STATE MACHINE
mechanics only — no CI wiring, no arming, no tenant-send integration (later slices).

## Unit — RC→promote state machine (design §state-machine), with four review notes as HARD requirements
1. Implement the RC state record + transitions as a module
   `validators/creator_engine_validator/release_acceptance.py` (NEW): states and entry
   evidence exactly per the design doc's table; state lives where the design says it lives.
2. REVIEW NOTE (2) RESOLVED: the `rc_marked → rehearsal_required` transition is an EXPLICIT
   GOVERNED ACTION (a recorded transition with actor + evidence ref), NOT automatic. Implement
   it that way and document the choice in the module docstring.
3. REVIEW NOTE (3) RESOLVED: promotion criterion 6 requires rehearsal-bundle fields
   (`rc_id`, `source_commit`) that slice-1 evidence format lacks. Implement the promotion
   check to REFUSE with a distinct `evidence_format_insufficient` reason when the bundle
   lacks those fields (fail-closed seam for the future harness slice; do NOT modify the
   shipped evidence format or harness in this unit).
4. REVIEW NOTE (1+4) RESOLVED: do not use the bare term "ring-0" in code/identifiers — use
   `dogfood_ring` (distribution tier) to avoid collision with `enforcement_ring: ring_0` in
   the seat/hook contracts; reference the design doc's consumer section by path in comments.
5. Tests `validators/tests/unit/test_release_acceptance.py` (NEW): every transition (legal +
   refused-illegal), the governed-action requirement (no transition without actor+evidence),
   the `evidence_format_insufficient` refusal, closure-integrity check (release ticket close
   requires linked acceptance evidence — as a pure function over plain data).

## Files (allowed writes)
The two NEW modules above, `.ce/changelog/ce-510-ship-gate-s2.md`, carrier
`.ce/pr-manifests/ce-510-ship-gate-s2.md` (slug=branch) with exactly:
`- **Declared work class:** S`. Product lens in prose.

## Stop lines
deploy/** (incl. deploy/rehearsal/**), .github/**, ce_cli.py, v3_cli.py, launch_runtime.py,
seat_reaper.py, doctor_runtime.py, checks/**, pr_preflight.py, forge/**, ticket_reconcile.py,
release_finalize* modules, docs/** (the design doc is READ-ONLY spec), .ce/brain/assertions.yaml.
