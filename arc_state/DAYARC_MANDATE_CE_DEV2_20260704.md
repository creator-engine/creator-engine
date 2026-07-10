# DAY-ARC MANDATE — CE-DEV-2 — 2026-07-04 (RATIFIED by Operator in-session)
> Operator: "the arc is ratified" + three Shape answers + appetite notes. This file = arc SSOT.

## Theme: retire the harvest/dispatch dependency (controller stops being the conveyor)
Autonomous approval JOINS the retirement (Operator, explicit). Ability to SCALE is the stated
priority driving the runtime-engine decision.

## ENDGOAL REFINEMENT (Operator, 2026-07-04 mid-arc — binding)
The arc's landing automation and the CONTAINERIZED-FIRST model are ONE endgoal, not two lanes:
the conveyor/belt/daemon automation this arc lands must run on the #437 canonical container
runtime (containers, daemons, everything — two-plane doctrine, systemd=adapter only). Host-
substrate deployments (e.g. A2's dev-1 user-systemd shadow units) are SHADOW/BRIDGE evidence
steps only — canary/live flips should land on the containerized form (#778 deploy/daemons +
deploy/queue-daemon artifacts) rather than deepening host patchwork.
ALSO standing (same beat): controller context >45% = definitive checkpoint + /clear.

## Shape answers (binding)
1. **Authority**: autonomous approval is in-scope of the retirement. Docs-class auto-approve+
   merge already ratified (ce-ops#356 Option A, 2026-06-30) and ARMED (`CE_AUTOMERGE_RUN_MODE=ceo`,
   #694 merged). EXECUTION GAP found 2026-07-04: armed tiers cover only carrier/changelog +
   brain-supersede path sets — narrower than the ratified docs-class envelope (that's why #771
   needed manual approval). Arc task: extend tier coverage to the full ratified ceo/docs envelope.
   Code-class stays per-PR (controller) until CE-410 slices 9-10 + Re-Arming Bundle → then a
   fresh R1 ratification for code-class.
2. **Harvest-daemon appetite**: one day-arc to working shadow-mode daemon (auto-opens PR from a
   READY seat, no auto-merge). Operator notes this is CONSERVATIVE → treat as floor: if shadow
   lands early in the arc, extend within the arc without re-asking.
3. **Belt arming**: shadow-first with a canary PR, then live. Ratified.

## ⚠️ PRIORITY DIRECTIVE (Operator, 2026-07-04 — binding for THIS arc AND the following night-arc)
Arad/Nitzan-related work (tenant constitution authoring, contributor onboarding, GitHub-plan
decision) takes LOWER precedence than the core lanes below: shipping a fully working CE to
either of them requires those platform issues fixed first, so the core lanes are the SOLE focus
for this arc + the next night-arc. Arad constitution = PARKED (finding banked: no constitution
file exists in the mythos repo — it needs AUTHORING, not just ratification). Nitzan onboarding =
PARKED pending details + this directive.

## Lanes (priority order)
- **A. Conveyor autonomy**: A1 harvest daemon (ce-ops#388 design→impl; shadow-mode milestone;
  born on #437 image, validation via CE-410 sandbox seam). A2 belt reactivation on dev-1
  (integrator_belt + review_pickup daemons, merged code, dark) — shadow → canary → live.
  A3 automerge tier extension to full docs-class envelope.
- **B. Two-plane #437** (appetite 2 arcs, arc 1 running): slice 1 ADR-0014 MERGED (#771);
  slice 2 portability guard DISPATCHED (dev-3); slice 3 containerize daemons/brokers queues
  behind A2 learnings; slice 4 published runtime image.
- **C. CE-410**: slice-8 SPIKE design DELIVERED (CE410_SLICE8_SPIKE_DESIGN_20260704.md),
  awaiting ratification + the runtime-engine decision (Podman-spike vs Docker+gVisor). Then
  8a→8b→8c→9→10 → Re-Arming Bundle (separate ratification).
- **D. In-flight flush**: #769 MERGED, #770 rework on dev-4, #772 walkthrough HELD (see E).
  #436 OneCLI implementation queues behind #437 slices 3-4 (reference topology banked:
  NanoClaw two-network isolation, mandatory-not-optional in CE's version).
- **E. CLI unification (ce-ops#440, Operator-ratified 2026-07-04)**: ONE user-facing `ce`
  command; binaries never encode versions; cev3 retired as user-facing name. Design pass
  running; #772 (walkthrough) held until the unified surface lands, then reworked against it.
  Engine decision + spike banked (rootless podman tier / Docker+gVisor seats / #439 port).

## Board at mandate time
dev-1 = #438 build · dev-3 = #437 slice-2 (queued behind residual task) · dev-4 = #770 rework.
Watchers: seat-signals, PR-board ×2, wall-daemon log. strangeLoop DISARMED (drift, ratified).

## Standing constraints
/clear dev-3+dev-4 before new dispatch · pointer+SHA briefs · territory check before dispatch ·
novelty check in every brief · full preflight one-pass green before push · controller never
self-reviews own authored work · main==live: code merges are deploys.
