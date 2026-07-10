# 🏭 DAY-SHIFT ARC MANIFEST — 2026-06-27 — "Shift into CEO gear"

**Author:** CE-DEV-2 controller (DGX Spark). **Date:** 2026-06-27.
**Purpose:** batch-ratify a CLOSED, bounded arc so it runs without Operator-as-bottleneck. Grounded in [[ce-autonomous-authority-doctrine]] (bar = consequence × novelty × irreversibility; GRANTED ≠ exercised), [[batch-strict-mode-gate-workflow]], [[ce-gate-authority-vs-containment-doctrine]], and [[ce-two-shift-arc-operating-model]].

**Strategic thesis (the why):** Our dominant autonomy gap is **run-mode, not tooling**. CE sits in **skynet × Dev** — we have the skynet topology (one operator → fleet) but drive it in the heaviest gear (controller hand-dispatches every ticket, hand-ratifies every PR). Peter Steinberger runs **solo × CEO/strangeLoop** — pre-decide scope, ratify on aggregated evidence, press merge. **This arc shifts CE skynet × Dev → skynet × CEO:** throughput / gate-amortization **leads** (the engine), the governance keystone (#289/#285) advances **one step behind** (the moat that makes it safe to extend across trust boundaries). We built the moat before the engine; this arc builds the engine.

**Companions (read for full reasoning):** `PETER_STEINBERGER_AUTONOMY_ANALYSIS_20260627.md` (the verdict + the 5 bets), `DAYSHIFT_ARC_INPUT_20260627.md` (the night-shift ledger + work-pool), memory `ce-gate-authority-vs-containment-doctrine`.

**Operator approval:** the arc shape "Shift into CEO gear", Waves 0–3, approved verbatim, including the priority inversion (lead throughput, demote #289/#285 to behind-the-engine).

**✅ RATIFIED 2026-06-27** — all three judgment calls confirmed as recommended: (1) build/flip split — BUILD+ARM the auto-merge engine under G5, **first live flip reserved to Operator (R2)**, armed on the lowest-risk class (docs-only / green / no public surface) and handed back as a one-gesture flip; (2) #218 modeled as a NET-NEW operational/deployment item (built-not-running), not a re-open; (3) #289/#285 advance one step behind the engine and do **not** gate Wave 1. **Status: GO.** Seat-prep (recon → harvest → refresh) precedes the first dispatch.

---

## THE WAVES (closed item-set)

Legend — **target:** `ctrl`=controller-driven, `fork`=controller's own fork/subagent, `dev-1/3/4`=fleet seat. **status:** EXISTING #N / NET-NEW (file first).

### Wave 0 — Clear the deck (cheap hygiene, fully parallel)

| ID | Status | Goal | Target | Surfaces | Deps | DoD / stop-line |
|----|--------|------|--------|----------|------|-----------------|
| **0.1 Tracker-drift close** | NET-NEW action | Close the 7 ce-ops issues with merged code still OPEN: #273/#274/#275/#286/#287/#288/#290 | ctrl | ce-ops issues only | none | All 7 CLOSED with a "merged in PR #N" comment. Stop if any has *un*merged scope (then it's real work, not drift). |
| **0.2 Close-bot diagnosis** | NET-NEW ticket | Diagnose why the merge-triggered close-bot (#262, merged) did **not** fire on the 7 drifted tickets — it's a throughput-automation bug (annoyance→tool) | fork | the close-bot workflow/code only | none | Root cause found + fix filed or applied; if fix is >1 small PR, file a ticket and stop. |
| **0.3 #558 unblock** | EXISTING #279 (PR #558) | Verify dev-3's CI fix; re-review + enqueue when green | ctrl gate + dev-3 | gate action | dev-3 pushes fix | #558 green + approved + enqueued, OR a fresh dispatch to dev-3 if still stalled. |
| **0.4 Nitzan day-one packet** | NET-NEW action | Send welcome packet (invite-confirmed; orient to CONTRIBUTING/contributing-to-ce/ce-playbooks + how-we-work + the gate + DCO) | ctrl/fork | comms only | none | Packet delivered. (She has already accepted all invites.) |

### Wave 1 — The gear-shift (THE SPINE — throughput / gate-amortization engine)

| ID | Status | Goal | Target | Surfaces | Deps | DoD / stop-line |
|----|--------|------|--------|----------|------|-----------------|
| **1.1 CEO-mode policy-tiered auto-merge** | NET-NEW ticket (THE top bet) | Pre-delegate low-risk classes (docs-only / all-gates-green / no public surface) to auto-merge with **no per-PR human gesture**; reserve a gesture for high-risk classes (security, deps, public surface, governance). Converts existing wall (#234/#239) + merge-queue from Dev→CEO. | fork (design) → dev-1/ctrl (impl) | merge-policy config + wall/queue glue + a policy-class classifier; **NO change to the wall's capability-token mechanism** | none (own trust domain — zero attestation needed) | Policy engine + class definitions BUILT, tested on a dry-run (classify-only, no live merge). **First live flip = R-series (Operator).** Stop at "armed but not flipped." |
| **1.2 AutoReview self-trigger** | NET-NEW ticket | Auto-fire a fresh-context reviewer-worker pre-PR-open / pre-merge, encoded as **one line in AGENTS.md** (steal Peter's trigger), not controller-dispatched. Reuse `reviewer` role + `/code-review`. | fork (wire) | AGENTS.md trigger line + a thin self-fire hook around existing reviewer | none | A PR self-triggers review without controller dispatch; evidence posted to the PR. |
| **1.3 Activate the belt** | NET-NEW operational ticket (#218 code CLOSED, **not running**) | Deploy the built belt (#218/#188/#200/#205 all merged) as an actually-running daemon so tickets self-pick instead of controller-dispatch — the ClawSweeper analog. | ctrl (deploy) + fork | belt daemon deployment/runner config (NOT new belt logic) | none | Belt daemon RUNNING + observed self-picking ≥1 real ticket in a staging/observed mode. **First unsupervised production run = R-series.** Per [[ce-fleet-deployment-surfaces]]: capability needs a RUNNER. |
| **1.4 Evidence-verified press-merge UX** | NET-NEW ticket (Mantis analog) | Aggregate gate evidence (diff + test results + review notes + computer-use video where relevant) into a **single ratification surface** so the human act collapses to "review the bundle, press merge". | fork (design) | builds on `computer-use-ticket` playbooks; evidence-bundle assembler | benefits from 1.1/1.2 but not blocked | Design + a working evidence-bundle for ≥1 real PR. Larger build may spawn a follow-up ticket (halt+amend). |

### Wave 2 — Parallel tracks (run alongside Wave 1)

| ID | Status | Goal | Target | Surfaces | Deps | DoD / stop-line |
|----|--------|------|--------|----------|------|-----------------|
| **2.1 ARC 2 #277** | EXISTING #277 | Carrier schema + SURFACE_UPDATE_RUNBOOK + validator check | dev-1 or dev-4 | surfaces/ + validator (check-adding now safe: #288/#555 merged) | none (unblocked) | PR green + gated. Reviewer checks count-agnostic assertion compliance. |
| **2.2 ARC 2 #278** | EXISTING #278 | `ce surfaces fleet-rollout` subcommand | dev-1 | surfaces/ CLI | **#279 must land first** | dispatch only after #558 merges. |
| **2.3 ARC 2 #280** | EXISTING #280 | Wire CI image build to source build-args from surfaces/render.py | ctrl or tightly-scoped dispatch | **`.github/**` (controller territory)** | #279 | controller-supervised; `.github` changes never blind-dispatched to a seat. |
| **2.4 Nitzan BUILD — file tickets** | NET-NEW action | File the BUILD-arc tickets: (a) ClaudeCodeAdapter impl [child of #110], (c) human-contributor schema role [child #137/#269], (d) trust-tier graduation criteria. (b) folds into existing #132. | ctrl | ce-ops issues | none | 3 tickets filed + linked to the onboarding plan. |
| **2.5 ClaudeCodeAdapter impl** | NET-NEW (child #110) | Implement the `ClaudeCodeAdapter` (#110 left a NotImplementedError skeleton) — the missing piece between the harness-adapter layer and a human using CE with Claude Code. | dev-4 or dev-1 | harness adapter module + tests | 2.4 filed | PR green + gated. |
| **2.6 #132 human-install** | EXISTING #132 | Drive S1 install blockers so a human (Nitzan) can stand up CE team-mode — the real product forcing-function. | dev-1 | installer S1 surfaces | none | S1 blockers cleared per #132 DoD; reviewer confirms human-path (not fleet-only). |
| **2.7 Keystone #289 + #285 (one step BEHIND the engine)** | EXISTING #289 + #285 | #289 SO_PEERCRED attestation (prove seat-origin, block host spoof) + #285 systemd socket-activation (broker survives restart; stop stranding contained seats). The team-mode/distributed-approval safety enabler. | ctrl or tightly-scoped fork (broker/systemd territory — **NOT a blind contained seat**) | tools/egress-broker/ + systemd units + audit logging | none, but explicitly **must not gate Wave 1** | Both PRs green + gated. Fleet-switch stays PARKED (R-series). |

### Wave 3 — Compounding habit (cheapest, most compounding)

| ID | Status | Goal | Target | Surfaces | Deps | DoD / stop-line |
|----|--------|------|--------|----------|------|-----------------|
| **3.1 Annoyance→tool reflex + agent-self-authored AGENTS.md** | NET-NEW ticket | Make "felt friction → build the tool" a standing controller reflex (Peter's #1 habit); let agents author/audit their own policy files (`AGENTS.md`). The close-bot bug (0.2) is its first input. | fork + ctrl | a lightweight reflex/runbook + an agent-authored AGENTS.md pass | none | Reflex codified as a playbook/runbook; ≥1 agent-authored AGENTS.md improvement landed. |

---

## CLOSED SCOPE STATEMENT

This arc is a **CLOSED manifest.** In scope = exactly Waves 0–3 above (4 + 4 + 7 + 1 items). Anything else — new programs, scope expansion on any item beyond its stated DoD, or a fork item that balloons past "1 small PR" — requires **halt + amend** (surface to Operator, do not absorb silently). NET-NEW tickets listed here are pre-authorized to file; net-new tickets *not* listed are out of scope.

## AUTHORITY GRANTS (G-series — pre-granted; each bounded; stop-conditions auto-halt)

- **G1 — Dispatch the arc.** Stock the queue, dispatch the listed items to their named targets via prompt-pointer+SHA, harvest, re-stock, /compact (>40% ctx, sequel) or /clear (wave boundary, new task) seats, spawn worker-forks — within this arc's item-set. BOUNDS: only the listed items; surface new out-of-arc scope before starting.
- **G2 — File the listed NET-NEW tickets** (0.2, 1.1, 1.2, 1.3, 1.4, 2.4's three children, 3.1) in ce-ops, linked to this manifest. BOUNDS: exactly these; no others.
- **G3 — Tracker-drift close** (0.1): close the 7 code-merged ce-ops issues. BOUNDS: only the 7 listed; verify each is truly code-merged first; stop if any has unmerged scope.
- **G4 — Gate merge authority (arc units).** Review-as-ce-dev-2, approve, enqueue PRs from this arc through the armed wall. BOUNDS: full host BASELINE-DIFF clean (zero NEW failures vs origin/main) + within arc scope + work-class declared. NOT: merging red, force-merge bypassing the wall, out-of-arc large diffs.
- **G5 — BUILD the CEO-mode amortization engine** (1.1, 1.2, 1.3, 1.4): design, implement, test, and **arm** (dry-run / staging / classify-only) the auto-merge policy, AutoReview self-trigger, belt activation, and evidence-merge UX. BOUNDS: built + armed + tested ONLY. The **first live flip** of auto-merge on a real PR class, and the **first unsupervised production belt run**, are RESERVED (R7).
- **G6 — Self-review canary + broker-health probe.** Run the from-seat self-review canary (dev-3 posts a COMMENT/REQUEST_CHANGES on a non-self PR via the review broker; capture audit evidence; APPROVE stays hard-refused). Add a broker-health probe to the cron backstop. BOUNDS: COMMENT/REQUEST_CHANGES only; no APPROVE; canary is read/comment, not a merge.

## RESERVED (R-series — stays Operator-gated)

- **R1 — Push-side fleet switch** (dev-1/dev-4 → vault-sourced self-push). Stays PARKED; needs #289+#285 landed + one-word Operator approval.
- **R2 — First LIVE flip of CEO-mode auto-merge** on any real PR class, and **first unsupervised production belt run.** Building + arming is G5; *flipping it on* is the Operator's gesture (it is the moment the human steps out of the per-PR loop — a deliberate run-mode change).
- **R3 — Granting any agent APPROVE authority** / weakening the wall's capability-token mechanism / making the broker's APPROVE-refusal policy-gated. (Distributed approval is post-#289, Operator-ratified.)
- **R4 — External-facing release / publish / real-user onboarding** beyond Nitzan's already-granted access (e.g. Arad, customers).
- **R5 — Git-history scrub** (NOT authorized). Irreversible destructive ops outside ratified sets (force-push to main, repo-settings, secret re-key).
- **R6 — New high-consequence scope** outside this arc's Waves 0–3.

## STANDING STOP-CONDITIONS (auto-halt → ⏸️ AWAITING-OPERATOR)

Bad merge / regression reaching main · any wall/Ring-1/containment guard failing to deny what it should · any credential surfacing in env/argv/transcript · two-strikes on any gate · an auto-merge dry-run that would have merged something it shouldn't · anything matching RESERVED.

## ENTRY CONDITIONS

- This manifest ratified by Operator. · Gate currently has only #558 open (low). · dev-1/dev-4 idle and ready; dev-3 finishing #558. · Brokers healthy post-night-incident.

## WHAT SUCCESS LOOKS LIKE (whole-arc DoD)

By end of shift, CE has **shifted into CEO gear**: the auto-merge policy engine + AutoReview self-trigger + a running belt are **built and armed** (awaiting only the Operator's one-gesture flip), so that the controller is no longer structurally required to dispatch every ticket and ratify every PR. The night's tracker-drift is cleared and its root cause (close-bot) fixed. ARC 2 is advancing toward completion (#277 landed, #278/#280 sequenced behind #279). Nitzan's team-mode BUILD arc is filed and moving (ClaudeCodeAdapter, #132). The governance keystone (#289/#285) is advancing **one step behind the engine** as the safety enabler — not gating throughput. The deliverable is a CE that, after one Operator flip, runs its own conveyor with the human reduced to ratifying aggregated evidence on the high-risk minority.

## STATUS: ⏸️ AWAITING OPERATOR RATIFICATION

Pending Operator: "ratify" (or reshape). On ratification → G1–G6 GRANTED with bounds; R1–R6/R7 reserved; arc runs autonomously with Operator available for unforeseen events.

### Judgment calls flagged for explicit Operator confirmation at ratification
1. **The build/flip split (G5 vs R2).** I scoped *building & arming* the auto-merge engine and *activating* the belt as pre-granted (G5), but the **first live flip** / **first unsupervised belt run** as Reserved (R2). Rationale: building is reversible and in-domain; the flip is the actual run-mode change where the human leaves the per-PR loop — that gesture should be yours. Confirm you want the flip reserved, or grant the flip too (full CEO-mode this shift).
2. **#218 is CLOSED but the belt isn't running.** I modeled "activate the belt" (1.3) as a NET-NEW operational item, not re-opening #218. Confirm that's the right framing (deployment surface, per [[ce-fleet-deployment-surfaces]]) vs. re-opening #218.
3. **#289/#285 demotion.** Already approved this turn, but it is load-bearing: they advance one step *behind* the engine and explicitly **do not gate Wave 1**. Confirm you're comfortable that the team-mode safety enabler trails the throughput engine within this shift.
