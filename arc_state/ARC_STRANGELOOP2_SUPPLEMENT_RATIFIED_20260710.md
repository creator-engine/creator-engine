# STRANGELOOP-2 SUPPLEMENT — OPERATOR-RATIFIED 2026-07-10
# Ratified verbatim by the Operator in the supervising session ("your recommendation …
# is approved along the rest that came after it"). Extends the ratified N-1..N-10 mandate.
# Author: supervising controller (DGX, read-only). Executor: main VPS controller.

## New mandate items

N-11 **Conveyor intake queue** — seats PULL ticket-units from an arc-fed queue instead of
     receiving controller-composed briefs. This is the single item that retires controller
     intake ownership (the missing piece of the 2026-07-08 intake-retirement ladder).
     Builds on N-4's brief-preflight: the composer's output becomes a queue entry, not a
     pane dispatch. Priority: immediately after N-1 slice 2 lands.

N-12 **Ticket-triage agent-organ (c5)** — seat-filed bugs/features triaged by a
     probabilistic agent-organ riding the deterministic belt feed, advisory-only disposal,
     per the daemon-vs-agent rubric (now docs/design/daemon-vs-agent-rubric.md via #932).
     Distinct from N-5 (stale-work reconciliation) — do not merge the two.

N-13 **Storage/gate incident fixes F-1…F-5** — full design in
     `.ce/state/research/VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md` (already in your
     research dir). F-1 (storage admission + reaper) and F-2 (gate hardening + liveness
     alarm) land AHEAD of the pending harvest wave; F-3 (migration-completeness runbook,
     incl. adding .claude/agents/ to the #931 snapshot manifest and declaring the UFW
     rule as IaC) lands this arc; F-4/F-5 close as evidence permits.

## Restored Operator-queue items (fell out of AWAITING-OPERATOR during the crash checkpoints)

R-1 **Materializer arming decision** — Option A materializer is built + unarmed (#902 lineage);
    arming is an Operator call. Put it back in the AWAITING-OPERATOR queue with a fresh
    one-page evidence summary (dry-run passes, IaC-redeploy precondition status per the
    singleton+IaC rule).

R-2 **#912 merge-intent confirmation** — PR #912 (ce-513 ratification-binding design) merged
    2026-07-09 while marked Operator-held. Confirm to the Operator whether its merge path
    included their preview/ratification; if not, present the merged design for retroactive
    review — it is the human-gate primitive and must not land unexamined.

## First governed roadmap snapshot

S-1 Run the #931 state-snapshot tool for its FIRST production snapshot, and include in the
    manifest: the intake-retirement ladder + autonomy dates, the dark-factory guide
    (.ce/state/research/ce-dark-factory-guide/), this supplement, the incident design doc,
    and .claude/agents/ (per F-3). Acceptance: a fresh controller on a third host can
    hydrate the roadmap from the forge alone. This closes the Operator's "our prose plan
    must not live on any single machine" directive.

## Ratified working pattern (record as doctrine)

P-1 **Multi-controller operator pattern** — an Operator may interface several controllers
    concurrently provided exactly ONE holds write/main authority (one-face); others run
    read-only supervision/diagnosis/design and interface through durable artifacts, never
    shared authority. Live-proven 2026-07-10 (this supplement is its artifact). Persist as
    a memory/doctrine entry and fold into the team-mode design inputs.

## Sequencing note
F-1/F-2 first (protects the wave) → harvest wave → N-1 slice 2 → N-11 → N-12.
R-1/R-2 are queue restorations — immediate, cheap, no code.
