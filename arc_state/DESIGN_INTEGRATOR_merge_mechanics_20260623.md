# DESIGN — The Integrator: CE's autonomous merge-mechanics agent

**Author:** CE-DEV-2 controller, 2026-06-23. **Status:** ratified-in-principle (Operator approved the recommendation + the role name "Integrator", 2026-06-23). **Home:** private `ce-ops/designs/` (internal planning — never public). **Related:** [[ce-merge-queue-offloads-mechanics]], [[ce-visibility-channel-emission-model]], [[ce-delegate-merge-conflict-triage]], [[ce-governed-seat-cannot-push]], [[ce-installation-grant-is-mint-ceiling]], [[ce-belt-feed-polling-default-push-premium]], [[openclaw-nemoclaw-stack]].

## 1. Problem — who owns rebasing in CE?

When a GitHub merge queue evicts a PR as `DIRTY / BEHIND / CONFLICTING`, *someone* must rebase it, resolve the conflict, re-green it, and re-enqueue. The merge queue offloads sequencing/testing/merge-commits to GitHub, but **no merge queue resolves semantic content conflicts** — that residue needs an owner.

Today that owner is **the controller, ad-hoc** — and only because a capable agent happens to be interfacing the Operator and managing the fleet. **This does not generalize.** A non-technical user in strangeLoop (80%) or CEO mode (15%) has no controller spinning up rebase workers; their approved PR stalls in the queue and they receive an unactionable *"merge conflict in `_versions.py`"* notification. So the current answer to "who owns rebasing" is effectively *"nobody, by design"* — the bug this design fixes.

(Concretely observed 2026-06-23: Wave-1 PRs #366/#367/#368 collided on `_versions.py` + `install.sh` after parallel dispatch; the controller manually fanned out three rebase workers to recover. That manual recovery is exactly the Integrator's designed job.)

## 2. Core principle — split mechanics from ratification

Two things have been conflated under "merging." Separate them:

| Concern | Owner | Reaches the user? |
| --- | --- | --- |
| **Merge MECHANICS** — rebase, conflict-resolve, re-green, re-enqueue | the **Integrator** (autonomous) | **Never** |
| **Merge RATIFICATION** — *should* this land | the governance/ratification gate (peer-review agents); user only in CEO mode | Only on a genuine **product** decision |

Mechanics are infrastructure and must be invisible. The user must never see a rebase. This refines [[ce-push-deploy-authority-model]]: *rebasing is mechanics → fully automate; the merge decision stays governed.*

## 3. Reference grounding — Claw's ClawSweeper (researched 2026-06-23)

Peter Steinberger's Claw ecosystem already built this, and the architecture confirms the split:
- **`clawpatch` (proposer) is explicitly NOT a lander** — "does not commit, push, open PRs, or land changes." It reviews/proposes only.
- **`ClawSweeper` (lander) owns the merge/repair lane.** Its automerge preflight maps `DIRTY/BEHIND/CONFLICTING` to *"repairable rebase work"* dispatched to a repair worker, not a parked status comment.
- **Repair pipeline:** adopt branch → **exact-head review before any change** → **deterministic mechanical resolvers** (isolated CHANGELOG conflicts, generated-config checksum three-way) → **LLM (Codex) fallback** that returns a *structured repair artifact* → **deterministic executor applies + pushes only after validation** → re-review → wait for required checks.
- **The LLM never holds write authority:** Codex gets a **read-scoped token**; ClawSweeper "creates write/check credentials only after Codex exits."
- **Merge gate = enumerable policy set:** merges "only after review verdict, checks, mergeability, security, maintainer stop/approve state, and repository policy gates pass." Human override via labels (`clawsweeper:human-review` / `approve` / `manual-only`).
- **Race-safety:** before pushing, waits 90s, re-fetches live PR head, **requeues instead of pushing if the head changed.**
- **Cloud shape is NOT a long-lived daemon:** ClawSweeper runs **ephemerally on GitHub Actions cron** (`*/5`); **Crabfleet** is a durable control plane that *"stores scheduling intent, run evidence, and policy"* but *"does not launch an autonomous executor."*
- **Contact model is maintainer-facing/technical** — a single mutable marker-badged PR comment + `@clawsweeper` commands. **No model for framing a conflict as a plain-language product question for a non-technical user** (confirmed absent in live sources) — **CE's whitespace.**

Sources: github.com/openclaw/clawsweeper, github.com/openclaw/clawpatch, clawsweeper.bot, docs.crabfleet.ai, openclaw.ai/ecosystem.

## 4. The Integrator — design

**Role:** a first-class CE role, **distinct from the review/build agents** (Claw's central lesson: proposer ≠ lander). Sole charter: own the path from *approved + green → landed in main*. It owns the mechanics of the **Ship** stage (landing), not the decision to ship.

**Architecture — control plane + scheduled-ephemeral contained execution** (the Crabfleet/ClawSweeper shape, which also fits CE's containment-everywhere posture better than a long-lived privileged daemon):
- **Control plane** (lightweight, persistent): subscribes to forge/merge-queue events (belt-feed polling default per [[ce-belt-feed-polling-default-push-premium]]); holds intent/policy/evidence/heartbeat; allowlist-gated GitHub App auth. Does *not* itself execute repairs.
- **Execution runs** (short-lived, contained): dispatched per repairable PR; do the rebase/resolve/validate in a sandbox; emit evidence; exit.

**Repair pipeline (deterministic-first, LLM-last, LLM-never-writes):**
1. **Adopt + exact-head review** before any mutation.
2. **Deterministic mechanical resolvers** for the common, unambiguous cases — `_versions.py` frozenset merges, changelog fragments, PR path-manifest carriers, lockfiles, generated configs, non-overlapping hunks. These cover the large majority and need no LLM.
3. **Read-only LLM resolver** (governed contained seat) only when mechanical resolvers don't fully apply → produces a **structured repair artifact**. The LLM holds **no write authority** — exactly CE's existing posture ([[ce-governed-seat-cannot-push]], minter-gate [[ce-installation-grant-is-mint-ceiling]]).
4. **Deterministic governed executor** (the spine/controller half) validates the artifact, mints write creds **only now**, pushes with `--force-with-lease`, re-greens.
5. **Re-enqueue with a settle-then-requeue race guard** (re-fetch live head; requeue, don't push, if it moved). Adopt Claw's 90s guard.

**Conflict PREVENTION (not just resolution):** the Integrator sequences PRs that touch shared files (manifest-intersection per [[ce-dispatch-ordering-discipline]]) instead of naively parallelizing them. Upstream structural fix for the worst offender: replace the single `_versions.py` registry with **per-module registration** so new-module PRs stop colliding (separate ticket).

**Escalation seam — CE's differentiator:** the merge gate is the human-in-the-loop boundary.
- **Mechanical conflict → never surfaced.** Resolved silently.
- **Product-decision conflict** (two changes semantically contradict — e.g., both rewrote the same business rule) → **translated into a plain-language choice** ("Feature A and B both changed how pricing works — which do you want?") and routed via the **contact-on-need / channel-emission layer** ([[ce-visibility-channel-emission-model]]; the `notify_feed` webhook sink shipped in PR #364) to the user's chosen channel (Discord/Slack/app). **Never a diff, never a conflict marker, never a technical label.** This is precisely the gap Claw leaves open.

**Dual-surface (adopt from Claw):** keep an auditable, in-band evidence trail on the PR (for the spine / Dev-mode users) **and** push the rare product-decision escalation out through the channel-agnostic gateway to where the non-technical owner actually lives.

**Governance:** the Integrator runs on the Ring-1 spine like every agent; every conflict resolution is evidence-logged, redaction-gated, and reviewable; the existing **ratification gate** (not new ad-hoc logic) decides autonomy-vs-escalate — a stronger version of Claw's label mechanism.

## 5. Composition — CE is already pre-disposed

The Integrator is largely an **assembly of pieces CE already has or is mid-building**, not a greenfield build:
- escalation channel = `notify_feed` / webhook sink (shipped, PR #364);
- read-only resolver = governed contained seat (can't push, §7);
- write-holding executor = the spine/controller;
- trigger = belt-feed polling;
- merge-policy gate = the existing ratification gate;
- containment substrate = the M2 container work (#208).

## 6. Adopt vs. differ (vs. ClawSweeper)

| Lesson | CE stance |
| --- | --- |
| Split proposer (clawpatch) from lander (ClawSweeper) | **ADOPT** — Integrator distinct from review/build agents |
| Deterministic-first, LLM-last conflict resolution | **ADOPT** |
| LLM gets read-only token; write creds minted only after LLM exits | **ADOPT** — already CE's posture; CE's strength |
| Merge-queue eviction = "repairable rebase work" | **ADOPT** |
| Settle-then-requeue race guard (90s + re-fetch head) | **ADOPT** |
| Merge behind an enumerable policy gate | **ADOPT** — CE ratification gate is a stronger version |
| Cloud = control plane + scheduled-ephemeral execution (not a daemon) | **ADOPT** — fits containment-everywhere |
| Escalation is maintainer-facing/technical (labels, `@` commands) | **DIFFER** — CE translates to a plain-language **product** decision via the channel layer (Claw's whitespace = CE's edge) |

## 7. Scope / phasing (for the ticket)

- **MVP:** on merge-queue eviction, deterministic-first repair for the common mechanical cases (`_versions.py`, changelog, path-manifest carriers) + re-enqueue with the race guard, riding the existing spine; escalate anything non-mechanical to the controller (initially technical, contained).
- **Phase 2:** read-only LLM resolver for harder conflicts; conflict-prevention sequencing; **plain-language product-decision escalation via the channel layer** (the differentiator).
- **Phase 3:** the persistent control-plane + ephemeral-execution split; per-module registration to eliminate the `_versions.py` collision class.

## 8. Open questions
- Exact trigger surface (merge-queue eviction webhook vs. forge polling) — defaults to polling per the belt-feed doctrine.
- Where the Integrator's authority is minted and bounded (GitHub App scope; allowlists) — reuse the per-dev identity / App-custody model.
- The taxonomy of "mechanical vs product" conflict — needs a concrete classifier (deterministic resolver coverage list + the escape hatch to escalation).
