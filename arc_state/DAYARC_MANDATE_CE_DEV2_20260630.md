# ☀️ DAY-SHIFT ARC MANDATE — CE-DEV-2 Orchestrator — 2026-06-30

> Drafted for Operator batch-ratification. Once ratified, dev-2 runs the lanes below autonomously under the granted authority (G-series); R-series stays Operator-gated. Resume anchor for the arc.

## Thesis
Massively scale CE's own dev throughput **using CE's product**, while landing the two time-critical anchors:
- **TODAY:** onboard the first external **test user (Nitzan)** + first **contributor**.
- **TOMORROW (01-Jul):** NVIDIA pitch (#74) — don't break the demo path; have evidence ready.
The arc converts the manual gate-tending I do now into *armed, governed autonomy* (seats + forge), and starts paying down the persistent-memory gap the company brain exists to close.

## Lanes (each: deliverable · Definition-of-Done · owner)

### L1 — Onboarding go-live + main-delivery (HIGHEST, time-boxed today)
- **Deliverable:** Nitzan can install CE end-to-end against the now-fixed live installer; first contributor has a working contribute path; AND the two main-delivery gaps closed.
- **DoD (today):** clean-room install e2e GREEN against live `creator-engine.dev/llms-install.md`; onboarding handoff doc updated; contributor path (CONTRIBUTING + first-good-issue) verified end-to-end (clone→ticket→governed-implement→PR).
- **L1.a — Clean-main-install (closes gap 1):** a governed one-command clean `ce` install BUILT FROM main HEAD (not run-from-source clone+venv patchwork) — applies the #207/#208 fleet-retirement clean-install to contributors. DoD: contributor gets a clean main install via one governed command; no manual venv/wheelhouse steps.
- **L1.b — Auto-track-main (closes gap 2):** a governed update mechanism that advances a contributor install to latest main HEAD (pull+rebuild+re-verify, governance intact) — `ce update --track main` or scheduled. DoD: one governed command (or schedule) keeps a contributor on latest main with preflight green.
- **Owner:** dev-1 (e2e today) + a seat (L1.a/L1.b build) + controller (handoff).

### L7 — Automatic GitHub releases (NEW)
- **Deliverable:** automate release cutting so test users (Arad+) always get the latest release without manual toil — CI builds release artifacts (pinned wheels + signed install spec), creates the GitHub release, publishes to Pages, on a release trigger (milestone/tag/cadence).
- **Signing interaction (R5):** the ce-root-v1 spec-signature is the ONE manual gate. Automation prepares the release to the signing point, surfaces canonical bytes for Operator signature, then auto-publishes post-sign. Target: a release cut with ≤1 manual act (the signature).
- **DoD:** triggering a release produces artifacts + GitHub release + published+verified signed spec with no manual steps beyond the single signature; release-parity guard green.
- **Owner:** a seat (build) + controller (sign-gate).

### L8 — SDD living-spec feedback loop (NEW, folded in 2026-06-30 — ce-ops#375)
- **Why:** audit found CE shipped FORWARD spec-driven development but NOT spec-kit's reverse/living loop (production/incidents→specs, requirement-change→flag-affected-plans). This loop IS our pitch ("grader outside the agent bridges present+future"). [[ce-sdd-feedback-loop-gap]]
- **Deliverable:** ratification-gated impact-propagation (detect+draft+flag, NEVER auto-mutate). Design DONE (architect, on ce-ops#375).
- **DoD (P0):** `downstream_refs` added to scope.schema.yaml + WARNING-only `ce_scope_impact` check (scope-content-drift via existing `ratified_scope_sha` + per-downstream-ref flags). P1=`ce scope impact`/`ce traceability`; P2=ledger→spec proposals.
- **Owner:** seat (2 PRs: schema + check) + controller. **Awaiting Operator greenlight to dispatch P0.**

### L9 — Docs surface (NEW, folded in 2026-06-30 — ce-ops#37/#374/#376)
- **Why:** website #docs = 7 RAW markdown links, no rendered portal. The OpenClaw-style portal (#37) was commissioned 2026-06-12, self-deferred "post-pitch," never milestoned, never in an arc → vanished. The #141 symptom-fix masked it.
- **Deliverable:** #374 pre-pitch rendered "What is CE"+architecture slice (pitch-critical); #37 full portal (post-pitch, now arc-visible); #376 process-hole sweep (unmilestoned user-stories invisible to arcs).
- **DoD:** a real rendered docs page reachable from the site pre-pitch; #376 sweep prevents recurrence.
- **Owner:** seat (#374 build) + controller. **Awaiting Operator greenlight to dispatch #374.**

### L10 — Work-management canon + process SSOT (NEW, folded in 2026-06-30)
- **Why:** reality map (`WORK_MGMT_REALITY_MAP_20260630.md`) found systemic term-collisions (story/Lane/Roadmap/Wave/Triage), no formal Backlog object, arc-lane assignment = 100% hand-curation with NO promotion mechanism (root cause of #37 vanishing), and NO work-management process SSOT.
- **Deliverable:** terminology canon (3 horizons + disambiguated terms) + a process SSOT + a promotion mechanism. Synthesis WITH Operator (like the tier canon).
- **DoD:** canon persisted to memory + a `ce-ops/process/work-management.md` SSOT + #376 sweep wired as the promotion safety-net.
- **Owner:** controller + Operator (synthesis); seat (SSOT doc + sweep build). **Awaiting Operator synthesis session.**

### L2 — Seats autonomy / CEO-mode arming
- **Deliverable:** AutoReview run_mode CLI activation (#346/#347) wired + coupled to strangeLoop arming; automerge actuator moved from dormant→**canary-armed** (bounded: tiny/story class, author≠approver, single-PR, audit-logged) behind a kill-switch.
- **DoD:** a real low-risk PR auto-merges through the armed path with full audit trail + the kill-switch demonstrably halts it; CEO-mode policy tiers (from closed #291) enforced.
- **Owner:** dev-4 (build) + controller (arming-flip = **R**, see below).

### L3 — Forge autonomy (triage)
- **Deliverable:** forge Triage Ready Queue (#67) — automated intake triage that labels/sizes/routes incoming issues into the ready queue.
- **DoD:** new issues auto-triaged (class, lane, ready/blocked) with an audit record; controller spot-checks.
- **Owner:** dev-3 (build).

### L4 — Company brain (persistent-memory paydown)
- **Deliverable (invariant-safe, not GPU-gated):** (a) **launch-hydration slice** — wire brain recall into controller launch context (fixes the recall-at-decision-moment failure); (b) **zero-LLM `[[wikilink]]` typed-graph layer** (gbrain's highest-ROI idea) as a derived/rebuildable recall leg; (c) eval upgrade (replay/qrels).
- **DoD:** brain recall demonstrably surfaces a stored convention into a fresh controller context; graph leg measurably lifts recall@k on the eval set; rebuild-invariant test green.
- **GPU-gated (→ R/deferred):** real self-hosted embedder ingest (blocked until coder frees GB10).
- **Owner:** dev-4 or dev-3 (build) + controller.

### L5 — Fleet health & hygiene (enabler — do first)
- **Deliverable:** (a) **contained-seat origin-refresh** — deliver current `origin/main` into dev-3/dev-4 containers so they stop re-doing merged work; (b) **codify** that refresh as a `ce`/runbook action; (c) restore the automerge/gate daemon + watchers; (d) prune ~210 stale worktrees.
- **DoD:** dev-3/dev-4 branch off current main; refresh is a one-command codified action; daemon + watchers alive; worktree count sane.
- **Owner:** controller + a worker.

### L6 — In-flight carry-overs
- #363-C egress (OpenShell delegation, interim) build → harvest; #365 (B-next) stays queued.
- #663 install-sig guard → flip advisory→**required blocking** (follow-up PR).
- Brief carriers/changelogs + author≠approver throughout.

## Sequencing
L5 (seat-refresh) **before** L2/L3/L4 dispatches (else stale-base PRs). L1 e2e runs in parallel now (dev-1 free). L6 fills gaps. Pitch-path (#74) protected: nothing in the arc may break the live install/demo before 01-Jul.

## 🟢 RATIFICATION BATCH — ✅ RATIFIED 2026-06-30 (G1–G7 GRANTED)
**Operator decisions locked:** D1 = canary envelope **tiny+story, author≠approver, single-PR, kill-switch, dev-2 override, audit-logged**. D2 = contributor **verify-path-only** today (access-grant = R4). D3 = brain L4 P1 pair **starts in parallel now**. Plus: L1 expanded with **L1.a clean-main-install** + **L1.b auto-track-main**; **L7 automatic GitHub releases** added. G5 scope now also covers L7 release-automation build (sign-step stays R5). G6 covers L4 brain build.

**Grants — what I may do autonomously this arc (RATIFIED):**
- **G1 — Merge gate:** approve (as ce-dev-2) + enqueue/merge any green, author≠approver PR across L1–L6. (No new spec-signing — that stays R.)
- **G2 — Dispatch & drive:** spawn governed workers (custom roles, most-efficient model) and drive seats (incl. context-refresh) for arc lanes without per-dispatch approval.
- **G3 — File ce-ops tickets** for arc lanes (gbrain P0–P3, codify-origin-refresh, triage, arming, etc.).
- **G4 — Seat origin-refresh:** deliver current `origin/main` into contained seats + re-task them (L5).
- **G5 — Build autonomy wiring:** build AutoReview run_mode + automerge-actuator arming + forge-triage code, **stopping before the live arming-flip**.
- **G6 — Brain build:** land launch-hydration + wikilink-graph + eval (invariant-safe; vector store stays derived/rebuildable; no per-token external models).
- **G7 — Daemon/watcher restore + worktree prune** (reversible housekeeping).

**Decisions I need from you (pick once):**
- **D1 — Autonomy canary scope:** when arming seats/auto-merge (the *flip*, R1), what envelope? (rec: tiny+story class, author≠approver, single-PR, kill-switch, audit-logged, dev-2 retains override.)
- **D2 — Contributor onboarding depth today:** verify the path only, or actually grant the first contributor access? (rec: verify path today; access-grant = your action.)
- **D3 — Brain priority:** L4 P1 pair now (launch-hydration + wikilink-graph), or hold brain until after onboarding+autonomy land? (rec: start L4 in parallel — it fixes a live failure mode.)

## 🟢 R-SERIES — ✅ RATIFIED 2026-06-30 (with conditions echoed) + #366 ratified-as-written
**#366** (main-HEAD artifact resolver/builder/verifier trust contract) = RATIFIED AS WRITTEN → unblocks L1.a/L1.b; dispatch the build (dev-1 holds the scout context → takes it post-L7).
- **R1 — live arming-flip: GRANTED**, exercised only AFTER the L2 canary is BUILT + verified, within the D1 envelope (tiny+story, author≠approver, single-PR, kill-switch, dev-2 override, audit-logged). Nothing built to arm yet.
- **R2 — real-embedder GPU ingest: GRANTED**, exercised only when the GB10 is FREE. The coder = another project; Operator checks it ~2026-06-30 10:00Z. Interim policy (deterministic brain) UNCHANGED — **do NOT stop the coder; exercise R2 after the GPU frees.**
- **R3 — releases sign-off: GRANTED** (release go/no-go). NOTE: **R5 (the ce-root-v1 cryptographic signature) was NOT in the grant and remains a per-instance physical act** — a release is authorized but each spec signature is still produced per-instance with the offline key.
- **R4 — contributor access grant: GRANTED.** To EXERCISE need: Nitzan's GitHub handle + access scope (outside-collaborator vs org-member; which repos; push-to-creator-engine-branch vs fork-only). Clean-main path also waits on the #366 build.
- **R5 — ce-root-v1 spec-signing: STILL per-instance** (not in the grant; the one non-delegable cryptographic act).
- **R6 — Anything irreversible/out-of-envelope beyond the above** → still auto-halt + surface.
