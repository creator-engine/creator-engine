# DAY-ARC MANDATE — CE-DEV-2 — 2026-07-02 — ✅ RATIFIED AS WRITTEN (Operator, ~09:15Z)

> Operator directives folded in (2026-07-02): (1) Knowledge-SSOT / anti-drift substrate =
> **utmost priority** (Steinberger conclusion: the dominant gap is run-mode amortization;
> every drift gate converts "controller must remember X" into "CI refuses X"); (2) the
> single-controller dependency (dev-2 = SPOF for the whole factory) must be remedied —
> IaC-deployable replacement controller now, multi-coordinator architecture long-run.
> Core convergence: **#166 memory→brain migration IS the de-SPOF prerequisite** — a
> replacement controller is only as good as the knowledge it can hydrate without a predecessor.

## Authority
Carry-over standing grants (merge/dispatch/wall/autonomy-canary; code ≤ M = 2-review
quorum, docs XS/S = single review). Reserved to Operator: R1-R6 unchanged (external
release/announce, history-scrub, beyond-envelope, irreversible-outside-set, new scope).
G-N3 conveyor arming stays REFUSED until ADR-0004 criteria met (impl + independent
security review + dry run). Ratified today: mirror-policy B/C/A (#732), ADR-0004 (#727),
#369=CI-derived, #320 ceremony (done — PR pending).

## LANES (priority order)

### D1 — Knowledge-SSOT / anti-drift substrate (LEAD LANE, ce-ops#166 + #314)
- D1a ✅in-flight: doctrine-coverage ratchet check (dev-3, branch ce-166-doctrine-coverage,
  class S) — CI refuses net-new uncovered docs/contracts/** doctrine.
- D1b: **controller-memory → brain migration** (the SPOF-breaking slice). Method: walk
  MEMORY.md topic files; each doctrine → (i) brain assertion w/ evidence claim
  (machine-checkable), or (ii) playbook/runbook SSOT doc (then covered by D1a ratchet),
  or (iii) explicitly retired. Batched (~10-15 doctrines per PR, S each). First batch =
  the doctrines a REPLACEMENT CONTROLLER would need day-1 (gate mechanics, dispatch/
  harvest procedure, seat-drive commands, preflight rules) — feeds #398 directly.
- D1c: #314 skill↔playbook anti-drift parity guard (bounded slice, S) — skills must not
  silently diverge from the playbooks they point at.
- D1d: seat-durable directives — AGENTS.md self-audit assertion (Steinberger steal #4):
  codify the foreman directive as a brain-checked artifact; verify post-compaction
  persistence mechanically (probe), not by recollection.
- Sequencing: D1a lands → widen governed_trees (contracts → architecture/decisions/
  operations/delivery) as fast-follow XS/S slices interleaved with D1b batches.

### D2 — Controller de-SPOF (NEW, ce-ops#398 Phase A + #397 Phase B)
- D2a: architect design pass for #398 (read identity-registry, brain_bootstrap seams,
  #181 hydration, duty inventory of THIS controller) → seed brief. Then implementer:
  runbook + standup script + duty manifest.
- D2b: **drill** (acceptance): stand up a replacement controller in a sandbox, one benign
  gate cycle end-to-end, gap list → tickets. Schedule after D1b batch 1 lands (knowledge
  floor) — target: this week, not this arc-day, unless capacity allows.
- D2c: #397 multi-coordinator ADR — dispatch design AFTER ADR-0004 impl experience
  (conveyor = the queue-mediated coordination prototype). Not today unless a seat starves.
- Interim mitigations TODAY (cheap): duty manifest extraction (D2a input); resume-state
  dual-write discipline continues; every new procedure lands as runbook not memory.

### D3 — Onboarding (Nitzan) — pitch-critical, same-day priority interrupt
- #320 agent-native install narration: ceremony DONE (re-signed, guard PASS, 157 tests
  green, preflight running) → push, PR (XS, single review), gate, live before first touch.
- Fast-lane any Nitzan-facing breakage/report: first-contact quality outranks D1 for
  same-day interrupts.

### D4 — Automation completion (N2 continuation)
- ADR-0004 payload-as-data-only redesign implementation (M, code): dev-4 on ce-390
  completion (dev-4 authored the ADR → may implement; G-N3 security review = distinct
  venue + criteria list in ADR §7). Then dry run → THEN arming decision to Operator.
- ce-ops#395: bump-to-main release automation slice (S) + release_orchestrate.py dead-code
  cleanup + tag-timing policy Q for Operator (queue it with evidence when a seat frees).
- ce-ops#369 redo (CI-derived artifact, ratified direction) — next free seat.
- In-flight gates: #733 fix + #734 fix (dev-1) → re-review → merge. #732/#727 merging.

### D5 — Hygiene (background)
- Prune merged review worktrees (wt-726/728/731/732 + wt-727 after merge).
- ce-ops#396 NITs (XS docs) — filler for an idle seat.
- MEMORY.md over budget (33.5KB/24.4KB) — D1b migration is the durable fix; trim index
  lines as doctrines move into the brain.

## SEAT ROUTING (foreman batches, file-disjoint)
- dev-1: #733+#734 fixes (in flight) → then D1b batch 1 (memory→brain migration, needs
  egress for gh evidence refs) or #369 redo.
- dev-3: D1a (in flight) → D1c (#314 parity guard) → D1a widen slices.
- dev-4: ce-390 (in flight) → ADR-0004 redesign impl (M, hardest-work-to-strongest-machine).
- Architect workers (controller-side, Sonnet): #398 design pass; L7 tag-timing follow-up.
- ⚠️ checks/__init__.py: ce-390 + ce-166 both hold 1-line claims — controller sequences
  at merge; NO third claim until both land.

## ⏸️ AWAITING-OPERATOR
1. THIS MANDATE — ratify lane set + priority order.
2. ce-ops#390 GitHub Support portal submission (text staged on the issue, ~2 min).
3. (later, with evidence) G-N3 arming decision; #395 tag-timing policy; #397 ADR ratification.
