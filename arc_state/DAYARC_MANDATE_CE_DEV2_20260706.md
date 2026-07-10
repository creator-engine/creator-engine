# DAY-ARC MANDATE — CE-DEV-2 — 2026-07-06 — ✅ RATIFIED (Operator ~03:2xZ, form: "arc ratified as written with D1-D7 answers" — R1-R8 granted)
> DECISION ANSWERS: D1=click NOW · D2=Arad same-day after canaries · D3=ADR-0005 RATIFIED
> per recommendation (+ amendment PR) · D4=arming decided after soak evidence · D5=#427
> folds into 0.3.3 · D6=Nitzan TODAY, reminder set +4h · D7=memory-audit APPROVED.
> Supersedes NIGHTARC_MANDATE_CE_DEV2_20260705_NIGHT.md on ratification (night log stays
> SSOT for what shipped: 12 PRs #835-#846, 0.3.2 released-to-the-click, dep-unlock SHADOW
> live, ADR-0005 merged-Proposed). Companion: RESUME_STATE_CE_DEV2_NIGHTARC_20260706T0300Z,
> ce-ops#465 (operator marker), ce-ops#466 (C5 attempt-2), MEMORY.md.

## State at drafting (~03:15Z)
Board empty; queue daemon healthy (host, post-rollback). Seats: dev-1 building #423,
dev-3 batch 10 (#458/#460), dev-4 ce-463. Awaiting Operator: click, ADR-0005, #427
sequencing, Arad delivery, memory-audit approval.

## ⏫ RATIFIED ADDENDUM (Operator, 2026-07-06 ~03:5xZ, form: "ratified as written")
0.3.3 MINIMAL POINT RELEASE authorized: #468 (cli_exposure verify regression — canary C
blocker) + possibly #462 (auto-tag token) once fix merges → controller cuts 0.3.3 off
CURRENT main (full ceremony, offline sig = controller's non-delegable act) → rerun canary
C vs live 0.3.3 → complete DoD/Arad pack → ⏸️ Operator sends SAME DAY (D2 stands).
Context: canary C RED on 0.3.2 (ce-ops#468); A+B PASS; findings batch ce-ops#469;
identity-recall gap ce-ops#470.

## Lanes
### D-A — 0.3.2 → TRACTION (first priority; release-to-traction doctrine)
1. ⏸️ CLICK (Operator): ghcr ce-seat → public; controller verifies anonymous pull.
2. Canaries A (fresh VPS one-liner), B (/var/tmp DGX llms-install agent-fed), C completion
   (controller-inline PEM apply vs ce-canary-sandbox, logged) — vs LIVE 0.3.2 artifacts.
3. DoD evidence pack → fold canary evidence into tmp/arad-pack-0.3.2/ (clear TODO-CANARY).
4. ⏸️ Arad delivery: Operator sends (D3 standing). Post-delivery: open tenant-feedback
   intake (ticket per item; #455-residual class).
5. Release-chain durability BEFORE 0.3.3: fix ce-ops#462 (auto-tag token → tag workflows
   fire) + wire ce-ops#457's lint into the ceremony playbook; file 0.3.3 candidate list
   (#427 fold?, #459 SHA256SUMS chain, #462).
6. DOCS CURRENCY (Operator directive 2026-07-06): (a) IMMEDIATE unit — README.md still
   says 0.3.0 (2 refs) vs live 0.3.2; dispatch docs-class fix (README + site version
   sweep, product-lens, rides L2 docs automerge); (b) FEATURE — autonomous doc updates on
   release + significant changes: ticket verified/filed by worker (release-time sync +
   version-drift CI gate (unsigned sibling of #457) + significant-change refresh trigger);
   schedule implementation as conveyor units once the ticket lands.

### D-B — conveyor + seats (continuous, no-idle)
Land in-flight: dev-1 #423 (per-tenant denylist matrix — review bars: config-object seam
per #839 review note, no weakened patterns) · dev-3 #458+#460 · dev-4 #463. Harvest/review/
merge each; restock from backlog (candidates: #461 e2e fixture, #464 sweep design, #426
G11 once #837-adjacent files settle, piece-4 seed ticket). #427: execute per D5 decision.

### D-C — brain integrity: ADR-0005 ratification → implementation slice 1
⏸️ Operator ratifies ADR-0005 (3 recorded amendments — recommend folding as a tiny
amendment PR at ratification). Then dispatch implementation slice 1 per the ADR's own
deferral list (append daemon skeleton + mediation evidence emission; merge-gate evidence
REQUIREMENT stays a later slice per §7). Evidence: tonight's 5 serializations; every
ledger-touching PR pays the tax until this lands.

### D-D — dark-factory: dep-unlock LIVE decision + piece-4
#463 lands (dev-4, in flight) → SHADOW soak with audit-artifact review (controller reads
would-unlock proposals vs reality) ≥2 arc-days → ⏸️ D4 arming decision (repo vars = ops
act, Operator ratifies; kill-switch supremacy verified in soak). Piece-4 seed (work_claims
lifecycle states) = file ticket + dispatch as file-disjoint unit. Pieces 3/5 stay design.

### D-E — C5 cutover retry (after ce-ops#466 fixes)
Dispatch #466 items 1-4 (adapter mixed-uid host-prep + mixed-uid smoke + per-attempt logs
+ default image tag) as one seat unit → merge → retry cutover in next genuine quiet window
(runbook + staging doc discipline; soak clock restarts). Podman migration stays post-#439.

### D-F — hygiene + contributor
⏸️ D7 memory-audit sweep (utility agent: diff every topic-file correction vs its index
hook; fix in same-edit pairs). #464 worktree-debt: dispatch the classified-sweep DESIGN
(not execution). Nitzan: ⏸️ D6 Operator answers the 7 open questions
(NITZAN_CONTRIBUTOR_PREP_DRAFT_20260705.md) → then CONTRIBUTING gap-fix PR (changelog +
work-class contributor docs) as first concrete unit.

## ⏸️ DECISIONS NEEDED (batch with ratification)
- D1 CLICK timing: now / later-today (everything downstream is autonomous after it).
- D2 Arad delivery: same-day after canaries (recommend) / hold.
- D3 ADR-0005: ratify as-is / ratify+amendment-PR (recommend) / hold.
- D4 dep-unlock arming: authorize post-soak flip now (recommend: decide after soak
  evidence, revisit tomorrow) / explicit hold.
- D5 #427: fold into 0.3.3 (recommend — schema stays in signed chain) / decouple seam first.
- D6 Nitzan: answer open questions today / defer.
- D7 memory-audit sweep: approve (recommend) / skip.

## Bounds (standing, unchanged)
Gate singleton; ce-root-v1 signing = this seat only (0.3.3 not being cut today unless
ratified); no arming beyond ratified envelopes (dep-unlock stays SHADOW pending D4);
external comms = Arad delivery by Operator only; R-class → halt → Operator.

## R-items for batch ratification
R1 Day-arc as drafted (D-A..D-F) · R2 canaries+DoD+pack completion on the click ·
R3 0.3.3 candidate list + #462/#457-wiring release-chain fixes · R4 ADR-0005 slice-1
dispatch after ratification · R5 dep-unlock soak-review authority (arming stays gated on
D4) · R6 C5 fix-dispatch + retry-in-quiet-window · R7 hygiene lane (memory audit per D7,
#464 design) · R8 Nitzan CONTRIBUTING unit after D6.
