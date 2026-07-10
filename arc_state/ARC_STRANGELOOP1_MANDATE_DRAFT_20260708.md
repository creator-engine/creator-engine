# ARC STRANGELOOP-1 — MANDATE DRAFT (co-planned 2026-07-08 evening; awaiting Operator batch ratification)

## Thesis
First deliberate test of the dark-factory end-state operating mode: Operator+controller co-plan
the arc, Operator ratifies ONCE, controller drives autonomously for ~9 hours — continuous
conveyor loops (dispatch→build→review→gate→merge→restock), zero idle seats, zero per-unit
Operator input. The arc is a formal EXPERIMENT: full telemetry, morning retro with design
conclusions, improvements feed the next loop iteration. (test → review → conclude → improve → repeat)

## Operating mode (the loop, not a task list)
1. Every seat carries a stocked file-disjoint batch at all times (idle+backlog = fault, restock first).
2. On READY/PR: fresh-context reviewer → controller fixes mechanical findings at harvest →
   approve as ce-dev-2 → systemd gate merges. Judgment findings → back to authoring seat.
3. On merge: restock the freed seat from the RATIFIED POOL below (ordered, pull next disjoint unit).
4. Gap discovered mid-unit → ops_triage files ticket; promoted to a unit ONLY if it blocks a pool unit.
5. Brain-ledger-touching units strictly serialized (one in flight, ledger-tail ordering).
6. Heartbeat watcher re-assesses the whole board every ~25 min (restock check, stall check, watcher health).
7. Checkpoint (RESUME_STATE) after every material event; arc ledger records every
   dispatch/harvest/verdict/merge with timestamps.

## Ratified pool (ordered; units pulled as seats free up)
IN FLIGHT (already dispatched under standing directive):
  P0. dev-4 batch: ce-conveyor-intake-s1 + ce-491-prearming · dev-3 batch: ceo-onboarding /
      seat-preflight-parity / readme-review-minors · dev-1: hermes R2 (on #907 merge).
POOL (next pulls, in order):
  P1. ce-ops#512 fixes — singleton-redeploy portability (render User, worktree .git support,
      probe env parity, host-agnostic RELOCATION) [well-specified by today's deployment evidence]
  P2. Acceptance-Evidence closure rule implementation — autoclose bot: Acceptance-Evidence field,
      warn-first enforcement, fail-open fix [ratification item 3]
  P3. ce-ops#509 Fresh-Tenant Rehearsal slice 1 — rehearsal harness scaffold (pinned clean
      container, install from signed release per docs, scripted CEO first-hour), evidence bundle
      format; NO gating flip in this slice [ratification item 2]
  P4. ce-ops#513 design unit — ratification-binding design artifact (derived approver_ref,
      authorization_source, operator inbox); morning Operator review; NO implementation [item 4]
  P5. ce-ops#511 seat-watch daemon slice 1 — productize idle-without-signal + dispatch-ack
      (containerized daemon template, dry-run default)
  P6. Controller host op: dev-4 DGX egress-broker deploy + dev-4 self-push canary (retires
      harvest role; already in ratified day-arc lanes)
  P7. Controller op: Ring-1 live governed `ce launch --harness codex` smoke + evidence packet
      (decision 4b, already authorized; FLIP still returns to Operator)
  P8. Review-daemon slice 1 — PR-opened → reviewer-spawn wiring, dry-run/advisory mode only
      (daemon wave; same containerized template)
  P9. Research unit (architect_research): closed-but-not-real sweep continuation from the
      directive-drift audit (recently-closed retire/migrate/automate tickets) → morning report.
EXPLICITLY OUT: Arad send · Nitzan D6 send · materializer ARMING · any L2-automerge-class
widening · release cut/signing ceremony · anything outward-facing or new-scope beyond pool+gap rule.

## Authority rails
- Approvals: ce-dev-2 approve+merge for pool units passing fresh-context review + FULL CI-parity
  preflight. Author≠reviewer preserved (seat/fork authors, fresh reviewer, controller approves).
- Seat lifecycle PRE-AUTHORIZED for the arc window: /compact freely; canonical `ce launch`
  relaunch when a seat crashes or exceeds the 45% ctx line (canonical method only, never raw codex).
- Incident authority: gate outage → IaC redeploy via the #895 surface from ~/ce-daemon-main
  (proven today). Seat/daemon anomalies → diagnose, restore via canonical/IaC paths, ledger it.
- Workers/seats never sign; controller signing stays within decision-9 scope (no release ceremony this arc).
- Session-limit crash risk (hit today 15:5x): mitigations = efficiency-routed subagents, systemd
  gate + seats survive controller death, checkpoint-after-every-event; on crash the next session
  resumes from MEMORY.md → DECISIONS → newest RESUME_STATE.

## Experiment instrumentation + Ship condition
- Arc ledger: .ce/state/research/ARC_STRANGELOOP1_LEDGER_20260708.md (append per event:
  ts, seat, unit, event, latency notes).
- Ship = morning ARC REPORT at .ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md:
  throughput (units merged/hr, PR cycle time), stall analysis (every idle-seat minute attributed
  controller/seat/gate), friction taxonomy (gate trips, review rounds, false-reds), Operator-input
  count (target: 0 during window), and DESIGN CONCLUSIONS → concrete improvements proposed for
  STRANGELOOP-2. Full paths on every artifact referenced.
