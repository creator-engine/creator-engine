# NIGHT-ARC MANDATE — CE-DEV-2 — 2026-07-04 (RATIFIED by Operator 2026-07-04 ~00:4xZ, as-is + L3 flip granted)
> Grounded in the N0 landed-state audit (dev-1, 2026-07-03T17:30Z, verified vs origin/main
> @ 842592c5c) — NOT in carried-forward lane lists. Day-arc shipped: CE-410 slices 1-5,
> #390 P0 closed (purge verified), 3 stale-queue corrections + novelty-check protocol change.

## VERIFIED STATE (from N0 audit + controller checks)
- DONE (do not touch): L7 auto-releases (incl #744 bump-to-main), close-bot #262, FleetIaC
  #377/#378, N1.5 docs (#696), ce-369 redo (#751), scanner coverage (#738/#741).
- ARMED + LIVE (controller-verified via repo variables): docs-class auto-merge
  (CE_AUTOMERGE_RUN_MODE=ceo, ref ce-ops#356) + Tier-B (carrier_changelog, brain_supersede
  both true since 2026-07-03). No kill-switch set. NO actuation has fired yet.
- PARTIAL: L3 triage (missing: ce-ops#67 sentinel-creation path + cron apply flip),
  L1.b (recall-floor residual only), conveyor daemon (code complete; disarmed BY DESIGN
  pending CE-410 slices 6-10 + slice-8 evidence bundle).
- NOT-STARTED: N5 worktree-prune, ce-ops#433.2 push-protection.
- Surface-B strangeLoop arming: built + deploy-templated, live broker still dev — R1-class,
  NOT a night action.

## NIGHT LANES (priority order)
- **G0 — CE-410 spine to the slice-8 gate.** Harvest #763 fix (in flight) → re-review (Haiku
  correctness framing) → merge slice 6 → dispatch slice 7 (ce410-validation-env-scrub, dev-4)
  → review → merge → then ASSEMBLE the slice-8 SPIKE ratification package (design refs,
  slices 1-7 merge evidence, arming-precondition checklist) and STOP. Slice 8 execution =
  Operator morning checkpoint. Slices 9/10 stay blocked behind 8.
- **G1 — Mythos tenant lane.** Harvest ce-422 from dev-3 (done-but-unsignaled, f2b0200d) →
  review → merge. Then dispatch ce-ops#432 to dev-3: tenant embedding-endpoint UX — config
  surface for the recall embedder endpoint (launch path currently hardcodes vllm-openai @
  localhost:8989) + VISIBLE degradation signal when recall hydration fails (today: one
  swallowed warning). Spec source: 2026-07-03 brain deep-dive.
- **G2 — L3 triage completion (dev-1).** Build the sentinel-creation path + cron apply flip
  behind a kill-switch variable. FLIP AUTHORITY: GRANTED (Operator, 2026-07-04 ~00:4xZ) — flip after build+test, kill-switched, spot-check first apply run.
  Build regardless; flip only if granted.
- **G3 — Tier-B first-actuation watch (standing).** On any auto-merge actuation: verify audit
  lines (tier + reviewer_venue + ledger_evidence), bank evidence, report in morning summary.
  Kill-switch on anomaly: `ce automerge-kill-switch on` (within envelope, reversible).
- **G4 — N5 worktree-prune tool (filler).** Governed `ce prune` for stale worktrees (repo +
  fleet seats; dev-4 has 20+). Story-class. Dispatch to whichever seat frees first.
- **G5 — ce-ops#433.2 push-protection design note (architect worker, read-only).** Options
  assessment only (GitHub secret-scanning push protection w/ custom patterns vs governed
  client-side pre-push in seats vs broker-side). Morning decision artifact.
- **G6 — L1.b recall-floor residual:** verify what remains vs #682; if trivial (S), fold into
  a seat's batch; else ticket it and leave.

## STANDING RULES (night)
1. NOVELTY CHECK FIRST in every brief + controller-side content verification (three-dot diff
   vs origin/main + merged-PR-by-slug) before EVERY dispatch — no exceptions, audit map
   notwithstanding.
2. Territory intersect vs .ce/claims/ + open carriers + live worktrees before dispatch.
3. Full validate-pr GREEN one-pass before any push; carrier harvest-side for contained seats.
4. Independent non-author review on all gate-adjacent/credential slices (6,7 + anything
   forge/). Haiku + correctness framing for daemon/hardening code.
5. Watchers re-armed each session; verify BLOCKED/READY regex against live pane renders.
6. Seat ctx hygiene: >40% used → compact/clear before dispatch.
7. Resume-state addendum per major event; morning summary at end of arc.

## AUTO-HALT → OPERATOR (R-class, untouched at night)
Surface-B strangeLoop flip · slice-8 SPIKE execution · slices 9/10 · conveyor ARMING ·
history rewrites · anything outside the ratified envelope · GitHub-plan/Arad/reviewer-
exemption decisions (AWAITING-OPERATOR queue).

## MORNING DELIVERABLES
1. Slice-8 SPIKE ratification package. 2. Tier-B first-actuation audit evidence (if fired).
3. L3 state (+flip result if granted). 4. ce-422/#432 Mythos lane state. 5. #433.2 design
note. 6. Corrections ledger (any new already-landed catches).

## OPERATOR DIRECTIVE (2026-07-04 ~01:2xZ, in-session)
- dev-3 and dev-4 are LOW ON CONTEXT: send `/clear` to the seat (herdr: "/clear" + Enter,
  verify the reset in the pane) BEFORE dispatching ANY new work to either. Applies to the
  next dispatch points: dev-3 ← #432 brief (post ce-422 harvest), dev-4 ← slice-7 brief
  (post #763 merge). Re-verify the foreman fan-out directive survives the clear
  (ce-codex-foreman-directive-durable: seats revert to inline after context loss — confirm
  ~/.codex/AGENTS.md carries the directive, re-send if the seat behaves inline).
