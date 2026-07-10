# NIGHT-ARC MANDATE — CE-DEV-2 — 2026-07-06 night → 2026-07-07 morning — ✅ RATIFIED (Operator ~17:2xZ: "night arc ratified as written, D1-D8 all yes")
> Supersedes DAYARC_MANDATE_CE_DEV2_20260706.md lanes on ratification (day log stays SSOT for
> what shipped). Companion: RESUME_STATE_CE_DEV2_DAYARC_20260706T1425Z.md (+ deltas),
> DECISIONS_20260706.md, ce-ops#471 program (#477-#484), ce-ops#485-#491.
> Controller: CE-DEV-2 (Claude). TOKEN POLICY stands: codex seats build, Claude = gate acts +
> judgment. Night mode: ASSEMBLE-ONLY for anything outward — ZERO external comms, no tenant
> sends, no signing ceremonies, no repo-settings/ops acts beyond pre-authorized items below.

## State at drafting (~17:1xZ)
Merged today post-clear: #869 #866 #865 #871 #867 (5). Merge lane: #859, #870, #873 (re-rebase
in flight). Round-cycles: #864 (R3 delta review dev-3), #868 R2 (dev-3), #872 R2 TOCTOU (dev-3).
Building: dev-1 (#477 slice D drill + #486 hints), dev-4 (#479 parity matrix + #480 promotion
packet). P0 takeover chain COMPLETE pending #873 merge. Launch smoke: PASS-WITH-FINDINGS
(#489/#490 filed). Serialization tax ticketed (#491). Wall daemon healthy. Codex standby
controller from afternoon — verify liveness before relying on it.

## NORTH STARS (the two clocks the Operator asked about, now being driven)
A. Containerized controller AT PARITY with non-containerized (parity-by-enforcement-layer per
   ratified definition; vault root / approval channel / last repair rung stay outside BY DESIGN).
B. WHOLE FLEET on containerized controllers, same signed CE version, same capabilities.
Tonight buys: the remaining wiring for (A) minus soak-time, and the homogeneity groundwork for (B).

## LANES

### N-A — PARITY CRITICAL PATH (highest priority)
1. Land the in-flight round-cycles: #873 re-rebase → delta-check → re-approve → MERGE (P0
   complete). #864 R3 verdict → gate. #868 R2, #872 R2 → harvest → delta re-review → gate.
2. C5 CUTOVER RETRY [needs D1]: merge-gate daemon into container (fixes merged since attempt-2,
   ce-ops#466; night = the quiet window). Success bar: container daemon processes ≥3 real queue
   cycles with evidence parity vs host daemon. INSTANT ROLLBACK to host daemon on any anomaly —
   rollback rehearsed, host daemon kept warm. Kill-switch supremacy verified before cutover.
3. #228 JIT credential injection BUILD [needs D2]: OpenBao prereqs DONE; dispatch the injection
   mechanism (broker mints scoped short-TTL token at request time into seat runtime; zero
   container-resident credentials; audit per mint; failure-direction tests). Build+commit-only
   overnight; live wiring to a real seat = morning act.
4. Contained gate-holding CANARY, SHADOW POSTURE [needs D3]: launch a contained controller via
   canonical `ce launch` + `ce takeover --dry-run` evidence chain (all ON MAIN as of today);
   it SHADOWS the gate (reads board, computes would-approve/would-merge decisions, writes
   evidence) with ZERO gate authority — gate singleton stays with CE-DEV-2 host-side. Its
   decision log vs my real gate acts = the parity soak evidence (dep-unlock precedent: ≥2
   arc-days soak before any arming decision).
5. Soak clocks start CONCURRENT (C5 soak ∥ contained-canary shadow ∥ dep-unlock shadow already
   ticking) — per the Operator's revised-estimate directive from the day discussion.

### N-B — FLEET HOMOGENEITY (north star B groundwork)
1. #479 parity matrix + #480 codex promotion packet (dev-4, in build) → harvest → review → gate.
2. Codex Ring-1 SMOKE [needs D4]: once #480 lands, run the Ring-1 smoke + record the promotion
   evidence packet (ratified decision 7 allows pre-containment promotion on live-proven packet).
   `promotion-approved` matrix cell flips only with Operator morning sign-off — packet+smoke
   evidence assembled tonight, cell stays deferred.
3. dev-4 CLEAN-INSTALL RELAUNCH [needs D5]: retire dev-4's run-from-source per the ratified
   fleet-retirement program — relaunch via canonical `ce launch` on signed 0.3.3 install with
   broker sockets wired (rebuild canon = ce-dev4-rebuild-and-launch-canon). Sequenced AFTER its
   batch5 units are harvested. Same-version fleet = first concrete (B) milestone.
4. dev-1 containment (#408) = PREP ONLY tonight: precondition (#475 read-lane) likely lands, but
   executing containment on the fleet's only research seat is a morning act with the Operator
   present. Tonight: verify #475 merged, stage the containment launch spec, dry-run it.
5. First CONTINUITY DRILL [needs D6]: if #477 slice D (drill harness) lands tonight, execute
   drill #1 — benign governed gate cycle proof via codex standby: takeover → posture → one
   no-op-class gate act on a designated test PR → hand back → evidence packet. Weekly cadence
   was ratified (decision 8); this is its first execution.

### N-C — TENANT JOURNEY (Arad-package program; ZERO sends)
1. #486 next-step hints (dev-1, in build) → land. The terminal teaches.
2. #485 doc pair (QUICKSTART copy-pasteable + HOW_CE_BUILDS_SOFTWARE concepts): dispatch as a
   docs-class unit. Review bars embedded from the ratified rulings: no bet/appetite user-facing,
   Goal/Done-when/Change-type trio, Budget opt-in aside only (% for subscription lane), CLI-
   anchored canonical journey (slash-commands = optional sugar), honest loop (not waterfall),
   packs LINK canon docs never duplicate. MUST teach the PROVEN tenant path from today's smoke:
   `ce brain init` (once) + `ce launch --backend host`, with the contained-default lane
   documented as hardening-in-progress (#490).
3. #487 `ce shape --from <prd>` (existing-PRD first-class, Arad's actual situation): dispatch
   build. #489 (onboard emits genesis ledger + G6 refusal names `ce brain init`): dispatch —
   directly extends today's refusal-that-teaches work, small, high tenant value. #490 contained-
   default lane (plan-time digest/mount/command validation + surfaced docker stderr): dispatch
   the plan-time-refusal slice.
4. Morning deliverable: consolidated ARAD-SEND READINESS note — what the pack session (yours +
   codex) still owns (T4 rewrite per spec), what landed tonight, the one decision left (md
   sources in bundle). NO pack edits by me (your territory), NO send.

### N-D — DARK FACTORY
1. Dep-unlock SHADOW soak: read tonight's would-unlock proposals vs reality, write the audit
   review to evidence. NO arming (D4 of day-arc stays Operator-gated on soak evidence).
2. #488 controller-agnostic memory slice 1 [needs D7]: decision/lesson record kinds through
   ADR-0005's mediated-append path + the machine-readable hydration contract consumed by
   `ce takeover`'s Hydrate phase. Build+commit-only.
3. #491 serialization slice 1: smallest real cut — wire ledger appends through the mediated-
   append daemon at merge time OR make reconciliation-set/taxonomy-count derived. Design+build
   the chosen cut; if design says "bigger than a night unit", split and ticket.
4. #482 host-ops broker v1 design + #483 bottom-out rule design + #484 ephemeral-controller seam
   design: dispatch as design-class units (P2 backlog; design-only, like #481 which shipped
   today). Restock material for seats as they free up.
5. Piece-4 claims lifecycle (#868) landing tonight feeds the conveyor's claim hygiene directly.

### N-E — CONVEYOR & CONTROLLER HYGIENE (continuous)
- Gate cadence: every landed unit gets harvest → independent review (in-process venue with
  staged artifacts — pattern proven today) → evidence-based gate act. No unreviewed merges.
- Multi-unit foreman loading stays STANDING (2-3+ units per seat, restock on signal).
- Checkpoint every ~90min + at every material state change; dual-write CE-DEV-1; decisions to
  .ce/state/decisions/DECISIONS_20260707.md as they occur.
- 0.3.4 ASSEMBLY ONLY: candidate list + changelog collation + release-staging prep. NO cut, NO
  signing (co-sign artifact regime ratified today — signing waits for morning ceremony).
- Watchers re-armed after every firing; codex standby controller verified and kept warm as
  takeover target (its hydration = today's checkpoint chain + decisions file).
- MORNING REPORT: scoreboard (merges, soak evidence, drill result, parity gaps remaining),
  AWAITING-OPERATOR queue surfaced FIRST (Arad send, Nitzan D6, #474 tenant half, promotion
  cell, dev-1 containment execute, dep-unlock arming, 0.3.4 ceremony).

## ⏸️ DECISIONS REQUIRED (batch — ratify as written or flag exceptions)
D1. C5 cutover retry tonight in the quiet window, with rehearsed instant rollback and host daemon
    warm. RECOMMEND: YES.
D2. Build #228 JIT injection mechanism tonight (commit-only; live seat wiring = morning).
    RECOMMEND: YES.
D3. Launch contained gate-holding canary in SHADOW posture (zero gate authority; evidence-only;
    starts the parity soak clock). RECOMMEND: YES.
D4. Run codex Ring-1 smoke + assemble promotion evidence packet tonight once #480 lands;
    promotion-approved cell stays deferred to your morning sign-off. RECOMMEND: YES.
D5. dev-4 clean-install relaunch on signed 0.3.3 with broker sockets (canonical launch, rebuild
    canon), after batch5 harvest. RECOMMEND: YES.
D6. Execute continuity drill #1 tonight if slice D lands (benign gate cycle on a designated test
    PR via codex standby, evidence-packeted). RECOMMEND: YES.
D7. dev-3 self-push arbitration (pending since morning): switch dev-3 commit-only → proven broker
    self-push for docs/code-class units (gate acts still mine; arbitration set updated).
    RECOMMEND: YES — the spine is canary-GREEN since 07-02 and it removes the harvest round-trip
    for the highest-throughput seat.
D8. 0.3.4 stays assemble-only tonight; cut+sign = morning co-sign ceremony. RECOMMEND: YES
    (confirmation, not a change).
HARD STOP LINES regardless of answers: no external comms/sends (Arad, Nitzan, public), no
signing, no dep-unlock arming, no mythos/repo settings changes, no ghcr publish acts, no dev-1
containment EXECUTION, gate authority never leaves CE-DEV-2, kill-switch supremacy respected.
