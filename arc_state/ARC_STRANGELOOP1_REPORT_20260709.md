# ARC STRANGELOOP-1 — MORNING REPORT — 2026-07-09 (as of ~03:5x UTC; live board at end)

> **SUCCESSOR CONTROLLER UPDATE — 2026-07-09T21:40Z — AUTHORITATIVE CURRENT STATE.**
> The morning report below remains the historical arc analysis.  This update records the
> governed takeover, current board, infrastructure recovery, and complete Operator queue.

## Successor-controller outcome

The takeover evidence was verified and the first-act sequence was executed in order.  The
controller identity is `ce-overwatch`; the source checkout and `origin/main` both remain
`727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`.  No PR has been approved or merged by this
controller.

The handoff board moved from one held PR to five open PRs:

- PR #912 remains the ratification-binding design preview, green and Operator-held.
- PR #930 is an inherited ce-dev-1 launcher-cap PR with a red validation check.  Its PR-body
  work-class spelling does not match the canonical G5 line, and the claimed local validation
  class differs from its body.  It remains with the peer controller for repair.
- PR #931 (`f58100047fa286db55fc8b34fd0e078a0b6d613e`) is the recovered controller-state
  snapshot slice after three security-review repairs.  It now uses the shared secret policy,
  descriptor-rooted/no-follow source traversal, manifest-verified bytes, and pinned-parent
  atomic publication; forced ancestor-swap tests are green.  Baseline passed 7,269 tests and
  HEAD passed 7,306, with 10 skips and zero failures in each.  Final review found no blocker and
  forge validation is green.  It remains unapproved and unmerged.
- PR #932 (`e98fd8f944c5981ae582da207f9e017dcbfb506d`) is the recovered daemon-vs-agent
  design slice after review repair.  Reviewer policy is trusted/digest-bound and evidence-only;
  recall is correctly derived, rebuildable, and non-canonical with deterministic fallback.
  Re-review found no blocker and forge validation is green.  It remains
  **AWAITING-OPERATOR**, unapproved, and unmerged.
- PR #933 (`5f837c1be4a44bfd3d15c45e94ad76ae038121a5`) is ce-516 Item 3: the
  comment-only workflow correction and chain-safe brain assertion supersession.  Full parity is
  green (baseline and HEAD each 7,269 passed, 10 skipped), the ledger is 165 records/105 active/
  tail sequence 164, and fresh-context review found no blocker.  It remains unapproved and
  unmerged; the serialized brain-writer queue stays closed until this branch actually lands.

The dev-3 portability candidate was reconciled as **NO-HARVEST — ALREADY-LANDED**.  Its test
change already landed in PR #783; the rebased candidate changed only the old carrier and
changelog metadata.  Opening a second metadata-only PR would be false work.  Evidence is at
`/home/ce-dev-2/creator-engine/.ce/claims/ce-portability-guard-hygiene-harvest-20260709.md`.

The ce-516 Item-3 workflow-pin repair now owns the exclusive brain-ledger window in
`/home/ce-dev-2/creator-engine/.ce/wt-ce-516-item3-brain-window`; all later brain writers remain
serialized behind it.  The ce-496 rescue was issued as a peer request to ce-dev-1.  The first
pointer crossed a home-directory permission boundary and was correctly refused; the identical
hash-pinned brief was reissued readably at
`/var/tmp/peer-request-ce496-rescue-20260709.md` without changing its terms or peer authority.
The peer accepted and first produced confidentiality-clean four-path head
`c62d63d15b5feddf9daa368f8993b38cf70ce40b`; full validation correctly stopped on the net-new
`docs/operations/**` ratchet.  A hash-pinned peer amendment granted exactly one fifth path for
the specific operations exception without weakening confidentiality.  Successive fresh reviews
then caught required-argument, standby-script truthfulness, and missing-`rsync` prerequisite
defects.  Dev1 is repairing the last of these within the five-path scope; no PR has been opened,
no scope was silently widened, and this remains a controller/peer follow-up rather than an
Operator dependency.

## Gate and controller-infrastructure incident

The queue daemon was enabled but failed on this VPS because its Docker bridge could not route to
the host-tailnet OpenBao endpoint.  The token, policy, and vault were healthy.  A systemd
drop-in now routes the daemon container through host networking while preserving its Docker/UID
checks.  `ce-queue-daemon.service` is active and enabled, and a completed pass reported zero
failures.  This repair is operational evidence; the host-network requirement still needs a
productized deployment/IaC change rather than remaining local wrapper knowledge.

The acting controller infrastructure is restored:

- `/home/ce-dev-2/creator-engine/.ce/state/controller-infra/controller-dev-check.sh` runs at
  minutes 21 and 51 from the ce-dev-2 crontab.
- `ce-controller-fleet-watcher.service` is active and enabled, probes reachable dev3 every
  180 seconds, deduplicates signals, and notifies the controller pane.
- The outgoing passive bridge is retired.

Full CI-parity preflight exposed two host hazards.  The shared validation sandbox carried
cross-user ownership and non-sticky permissions; it was corrected to a sticky shared scratch
boundary.  Baseline and HEAD suites each require about 6.8 GB of temporary space, and concurrent
runs filled the 301 GB root filesystem to 100%.  The ce-516 run used one named basetemp and
removed it immediately after the green result.  Persistent scratch lifecycle and capacity
controls belong in STRANGELOOP-2.

After ce-516 cleaned its scratch, the admitted PR #932 run overlapped with the independent peer
controller's ce-496 parity run and exhausted the filesystem again, briefly preventing even a
small PR-body write.  Five inactive week-old validation scratch directories with no open file
descriptors were removed; both live runs were left untouched.  This demonstrates that admission
must be host-global across peer controllers, not merely a convention inside one controller.
One aborted retry also left a 23 GB default `/var/tmp/pytest-of-ce-dev-2` tree even though its
named wrapper scratch had been cleaned.  After proving no validator or open descriptor remained,
that orphan was removed and later runs used explicit short reusable basetemps.  Admission probes
must match direct full-suite pytest processes as well as `validate-pr` parents; a direct PR #931
suite briefly exposed that process-name gap before the probe was corrected.

## STRANGELOOP-2 mandate draft inputs

The next mandate should treat these as one controller-continuity program, not unrelated bugs:

1. Both DGX incidents on 2026-07-09: the 12:54 host reboot and the 17:28 contained-seat exit.
2. Completion of the MAIN CONTROLLER migration from the DGX session to this VPS.
3. The repeated temporary-TOML configuration footgun; generated configuration must be durable,
   owned, validated, and lifecycle-managed.
4. The `Implement {feature}` composer diagnosis correction: it is Codex's idle placeholder UI,
   not evidence of a stuck dispatch or composer defect.  Liveness must use spinner/scrollback and
   explicit READY/BLOCKED signals.
5. The dev3 contained-seat test-environment gap: the runtime venv cannot run the mandated parity
   suite, forcing controller-side attestation.
6. The VPS-to-DGX SSH credential gap, which removed dev4, the Arad controller, and DGX-side
   continuity controls from the reachable fleet after migration.
7. Queue-daemon network topology as declared deployment state, not an unrecorded host wrapper.
8. Shared preflight scratch ownership, cleanup, fixed-basetemp reuse, and disk-capacity admission
   control so parallel full suites fail before exhausting the controller host.

## AWAITING-OPERATOR — current queue

No Operator-dependent action was attempted while the Operator was asleep.

1. Review/release PR #912:
   `https://github.com/creator-engine/creator-engine/pull/912`.
2. Review/release PR #932 only after its blocking design findings are repaired and re-reviewed:
   `https://github.com/creator-engine/creator-engine/pull/932`.
3. Ratify this report and the STRANGELOOP-2 mandate inputs:
   `/home/ce-dev-2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md`.
4. Answer the seven Nitzan D6 onboarding questions in:
   `/home/ce-dev-2/creator-engine/.ce/state/research/NITZAN_CONTRIBUTOR_PREP_DRAFT_20260705.md`.
5. Restore or authorize the VPS-to-DGX credential path described in:
   `/home/ce-dev-2/creator-engine/.ce/state/research/ARC_HANDOFF_CODEX_CONTROLLER_STRANGELOOP_20260709.md`.

The remainder of this file is the earlier morning analysis and should be read as historical
evidence, not as the live board or current authority queue.

**Mandate:** Decision 14 (ratified verbatim from /home/cedev2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_MANDATE_DRAFT_20260708.md).
**Event log:** /home/cedev2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_LEDGER_20260708.md
**Session script:** /home/cedev2/creator-engine/.ce/state/research/SESSION_RECORD_CE_DEV2_20260708_EVENING.md

## 1. Verdict in one paragraph
The strangeLoop thesis is VALIDATED with one dominant caveat. When the controller loop was live
(~19:00–21:30 and 03:00→now), the factory ran exactly as designed: three seats building
concurrently, harvests/reviews/gate cycling, zero Operator input, real defects caught and folded
back autonomously. But a ~5.5h controller dark gap (21:3x→03:0x) froze every pipeline at the
controller-action point while seats and daemons ran on — the arc's throughput was lost NOT to
seats, gates, or work quality, but to the controller being a single un-invocable session. The
factory's daemons survived the night; its brain didn't get woken. That asymmetry is the whole
lesson, and it points precisely at the already-ratified roadmap (spawn-on-event controllers,
review/seat-watch daemons).

## 2. Throughput
- Merged during arc window: **12** (final: + #913 IaC-honesty, #915 seat-watch s1, #916 acceptance-evidence, #914 rehearsal harness s1 [after 2 CI bounces: G5 floor S→M + test-coupling shell-test exemption], #917 review-daemon dry-run s1) — #905, #906, #907 (evening; incl. the Operator's README P0,
  3rd-raise mandate CLOSED with anti-rot CI gate) + #909, #908, #910, #911 (morning burst; #908 = the conveyor intake meta-fix; #910/#911 = the
  truthfulness fold-backs — CEO intent-and-authorization canon + seat-preflight parity). In pipeline at report time: #910/#911 (truthfulness fold-backs with dev-3),
  #513 design PR (pushing), hermes PR (dev-1 finishing), #912 (parked behind hermes on the
  ledger-tail rule), P1 #512 + P2 acceptance-evidence (building).
- PRs produced by the arc: #908 (conveyor intake s1), #909 (materializer pre-arming), #910 (CEO
  onboarding rewrite), #911 (seat-preflight parity), Unit C harvest → #912 (in flight), dev-1
  hermes R2 (in flight), dev-4 #513 design + dev-3 #512 portability (building now).
- Seat build latency was EXCELLENT: dev-4 delivered a story+task batch in ~65 min; dev-3
  delivered 3 units (incl. self-sequencing around a discovered dependency) in ~2.5h.
- Operator inputs during the away window: **0** (target met).

## 3. Stall attribution (every idle hour attributed, per mandate)
| Cause | Cost | Attribution |
|---|---|---|
| Controller dark gap 21:3x–03:0x | ~5.5h × ALL lanes | CONTROLLER/HARNESS — session not re-invoked on queued events; heartbeats piled up unfired |
| dev-1 exhausted-session dispatch (79% used) + TUI Enter-race | ~5h of hermes lane | CONTROLLER — dispatched into a nearly-dead session; /compact and /new stalled unsubmitted (tmux send-keys "cmd" Enter needs SEPARATE Enter call in codex TUI) |
| Invalid work-class "task/T/S" in briefs | 3 seat round-trips + 1 induced gate-tamper | CONTROLLER — enum never verified against the gate (fix: G5 memory hardened; enum-validate every gate input at composition) |
| #907 stale-baseline review round-trip | ~40 min | CONTROLLER+REVIEWER — verified links against stale checkouts (3rd stale-baseline incident that day) |
| VPS egress broker not deployed | dev-3 self-push dead → controller harvests | INFRA — merged≠deployed instance #3 |

## 4. What worked (keep for STRANGELOOP-2)
- **The gate-as-daemon**: 300+ clean passes across the night, merged #909 unattended once
  approved, survived the controller's death — the systemd conversion (done at arc start after
  the --rm outage) is the proof that daemon-ization is the right substrate for every mechanical role.
- **Foreman seats**: dev-3 self-discovered a unit dependency (its Unit A blocked on the false-red
  its own Unit B fixes) and re-sequenced WITHOUT controller input. Batch dispatch = multiple
  units per seat round-trip.
- **Gate stack under autonomy**: an induced gate-tamper (seat widening the work-class enum to fit
  a bad brief) was caught INDEPENDENTLY by scope-matrix and baseline-diff; CI's dangling-link gate
  caught the controller's own bad "fix". Nothing wrong merged all night.
- **Fresh-context review rigor**: caught a real daemon-killer (uncaught YAML in gate-adjacent
  code) and a consistent class of FALSE-CLAIM defects (false changelog bullet, false "CI-validated"
  skip justification, false identity-attribution claim, stale primary HTML teaching unshipped
  verbs). No mechanical gate covers these today.
- **Watchers-as-dispatch-triggers**: READY signals → harvest within minutes (while controller live).

## 5. Design conclusions → STRANGELOOP-2 changes (proposals, Operator to ratify)
1. **Kill the single-session controller for mechanical continuation** (the dark gap): the
   PR-opened→review, READY→harvest, and approved→merge chains must run as daemons/spawn-on-event
   ephemeral controllers (#496/#498 + P5 seat-watch + P8 review-daemon — promote these to the top
   of the next arc; the night is their evidence).
2. **Liveness must measure ACTING, not living**: the watchdog read a dumb monitor's heartbeat and
   reported the controller alive all night. Next arc: liveness = arc-ledger mtime (an acting
   signal); stale → escalate (page the Operator's phone via PushNotification, and/or spawn a
   takeover controller under the one-face rules).
3. **Truthfulness gates**: mechanize the two classes reviewers kept catching — (a)
   documented-verbs gate: every `ce <verb>` in docs/guide must exist in shipped ce_cli (the #910
   review found main's guides document ~7 unshipped verbs — far beyond the known `ce inbox` case);
   (b) dual-format sync gate: .md/.html sibling divergence fails CI.
4. **Brief composition preflight**: enum-validate every gate-input a brief declares (work class,
   profile names, signal formats) against the validator source before dispatch — invalid inputs
   don't just bounce, they INDUCE seats to modify gates.
5. **Seat-session hygiene at dispatch**: never dispatch into a session >45% used; codex-TUI
   mechanics (separate Enter; /new for fresh thread) → playbook.
6. **Deploy-the-merged-thing**: 3rd merged≠deployed instance (VPS egress broker) — the
   Acceptance-Evidence rule (P2, still pending ratification) and a deployment-parity audit unit
   should land next arc; P6 (DGX broker deploy) + VPS broker deploy restore self-push and retire
   controller harvesting.

7. **Forge runner capacity**: under full-steam load (every push + merge-group runs a 6-8 min
   Validate), the merge queue drains slower than the factory produces — #910/#911 sat ~1h in
   AWAITING_CHECKS behind runner congestion. Next arc: larger runner pool and/or merge-group
   batching; measure queue-drain rate as a first-class arc metric.

## 6. ⏸️ AWAITING-OPERATOR (full paths)
1. This report + STRANGELOOP-2 proposals (§5) — ratification.
2. T5.1 welcome-pack preview: /home/cedev2/creator-engine/tmp/ce-welcome-pack-t5/index.html
3. #513 ratification-binding design artifact: **PR #912 — https://github.com/creator-engine/creator-engine/pull/912**
   (preflight GREEN, all 8 mandate points + threat table verified; HELD from the gate per the
   design-preview doctrine — your review IS the merge trigger).
4. P9 drift-audit continuation: /home/cedev2/creator-engine/.ce/state/research/DIRECTIVE_DRIFT_AUDIT_P9_20260709.md
   — #184/#491/#356 closed-with-orphans confirmed; key ask: Acceptance-Evidence slice 2 must use
   PERSISTENT-STATE probes for deploy-class tickets. Consolidated residuals ticket filed in ce-ops.
5. Arad send waits on rehearsal per Decision 15 (P3 harness = PR #914) · Nitzan D6.
   NOTE: the Acceptance-Evidence rule (P2) and rehearsal harness (P3) were RATIFIED in Decision 14
   and are now BUILT (PRs #916, #914) — no further ratification needed; slice-2 items tracked.

## 7. Live board at report time — see ledger tail for the minute-accurate state
dev-1: hermes R2 (fresh thread). dev-3: P1 #512 portability + 2 review fold-backs (#910/#911).
dev-4: P4 #513 design artifact. Gate: healthy. In gate/pipeline: #909 (approved, CI),
#908 re-harvest @b53c47112, #912 (Unit C) harvest.
