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

## N-14 — dev-1 containment (Operator-ratified addition, 2026-07-10)
Execute ce-ops#408 (OPEN since ratification; never executed — confirmed by docker/podman
history, SSOT registry annotations, and the on-disk PEM flag): retire dev-1's run-from-source
tmux controller and relaunch it as a contained seat via canonical `ce launch` (dev-4 rebuild
canon = template; dev-3's codex-runsc image lineage = base). Includes: drain-or-hand-off its
queue first; migrate its App PEM to OpenBao per the registry TODO; F-5 residue policy applies
until cutover, then dies with the tmux. Evidence file: the 2026-07-10 storage incident (127G
unmetered residue) + dev-1 being the last ungoverned credential-holding writer on the fleet.
Sequencing: after F-1/F-2 + wave drain — do not decommission the proven workhorse mid-backlog.
This closes the LAST item of the whole-fleet containment mandate.

## N-15 — Silent-stall detection pair (Operator-ratified addendum, 2026-07-10, "approved as written")
Context: third silent-stall incident in ~30h (gate outage, dev-3 mutual-wait deadlock, 7-PR
uniform CI red). Root class: every component works as designed; the design has no
negative-space detection — silence is indistinguishable from progress. Two fixes close it:

**N-15a — Gate skip-anomaly alarm** (extends F-2.3; deterministic, in the queue daemon):
if skip_count with an IDENTICAL skip reason persists ≥ K consecutive passes (start K=3),
emit a distinct alarm event + page. Uniform identical reds across the queue are the
fingerprint of a rubric-change/main-poisoning event, mechanically detectable in two lines.
Include the oldest-approved-PR-age SLO in the same slice: approved & unmerged > N passes →
same alarm path.

**N-15b — Post-merge COMPOSITION probe** (scoping sharpened 2026-07-10 after pipeline
walkthrough with the Operator): the plain main-tip run ALREADY EXISTS (validate.yml
`push: main` trigger) and stayed green through this incident — main was poisoned only in
COMPOSITION, never in isolation. The unit is therefore the second clause alone: after every
merge to main, if the queue is non-empty, recompute ONE representative open-PR pairing
(merge that PR's head into the new main tip in a throwaway worktree — equivalent of its
merge-group tree) and run the validator suite FROM THE MERGED TREE (so new-landed tests
judge the old-world PR, exactly the #935 mechanism). Red → auto-file the incident naming
the breaking commit + page, BEFORE the next PR queues behind the poison. Rationale
(the perishable-green law): a green check is a perishable fact about a pairing (PR × main-
at-a-moment), never a durable property of a branch; #935's guard registration made every
old-world merge-ref red uniformly — this run converts hours of bisect into a 60-second alert.

Sequencing: N-15a into the current F-2 gate-hardening slice (same unit if it hasn't shipped);
N-15b as its own small unit immediately after the current CI-red fix-forward lands (it is the
regression test for this very incident). Both are detection-only — no new mutation authority.
