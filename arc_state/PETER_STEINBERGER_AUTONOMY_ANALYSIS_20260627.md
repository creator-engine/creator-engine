# Peter Steinberger vs. CE — Autonomy Gap Analysis (2026-06-27)

> Operator end-goal: **"Steinberger-level autonomy."** This measures CE honestly against his OpenClaw model, locates the dominant gap using the deployment×run-mode yardstick, and renders the verdict on whether #289/#285/team-mode are the right next bets.
>
> Source basis: Stage-1 extraction of Peter's MS Build talk ("build the thing that builds the thing") + CE's verified current posture. Companion: `RESUME_STATE_CE_DEV2_MORNING_20260627.md`, memory `ce-gate-authority-vs-containment-doctrine`.

---

## TL;DR

- **The dominant gap is RUN-MODE, not tooling.** Peter operates at **CEO/strangeLoop** (pre-decide scope in `vision.md`, look at aggregated evidence — a video, a close-report — then *press merge*). CE operates almost entirely in **Dev mode** (controller ratifies every PR by hand, dispatches every ticket, hand-patches the conveyor). We built a Ferrari gate — the credential wall + brokers + attestation — and we drive it in first gear.
- **We built the moat before the engine.** CE has *more* governance than Peter (attestation, the capability wall, egress control, signed ratification) and *less* throughput. Peter reaches massive autonomy with **zero** attestation/signing/wall because he runs a **single trust domain** — everything he runs, he trusts; the only gate is his own eyeball.
- **Governance is a moat, NOT a tax — but only relative to the team/skynet cells where parties don't trust each other.** For our internal solo-operator-throughput goal *right now*, prioritizing #289/#285 *ahead of* the throughput engine is a tax. They are the right MOAT and become critical the moment we onboard untrusted parties (Nitzan today; customers later) — but they do not themselves produce a single PR/hour.
- **Verdict:** #289 + #285 + team-mode are **right but mis-sequenced as "top priority"** if the metric is Steinberger throughput. Build the **run-mode amortization + compounding-throughput engine first/in-parallel**, keep #289/#285 moving as the team-mode safety enabler — engine slightly ahead of moat.

---

## 1. Side-by-Side Capability Map

| Peter's primitive | What it does | CE analog | Verdict | Honest note |
|---|---|---|---|---|
| **CrabBox** | Fresh remote VM per task, rsync-in, run tests, discard; multi-provider failover | Isolated git worktree per worker + gVisor/herdr containment + remote seats (dev-1/3/4) | **AHEAD (rigor) / heavier** | CE adds container-level isolation + cred-brokering Peter doesn't have. His is VM-level only — but deployed at scale and dead simple. We're more secure, less subnet-elastic. |
| **ClawSweeper** | GH Action → Codex per issue → reads `vision.md` → auto-close/comment. Closed ~15k issues | The **belt** (#218 poller, #188 reviews-pickup, #200 lane-claim, #205 launch-leg) | **BEHIND** | His is a running GH Action closing 15k issues. Our belt is **built-not-running** — needs the daemon RUNNER (#218 belt-poller→daemon). We *simulate* it manually via controller cycles. Over-architected vs a simple Action. |
| **AutoReview** | Codex-calls-Codex fresh-context review before every commit, triggered by **one line in AGENTS.md** | `reviewer` role + `/code-review` skill + merge-gate review | **BEHIND (the AUTO part)** | The capability exists; the **self-triggering loop does not**. CE review is controller-*dispatched*, not policy-auto-fired pre-commit. This is a cheap, high-value steal. |
| **Mantis** | PR ping → CrabBox → video of bug → fix → video of fix → verify → post. "Look at the video, press merge" | `computer-use-ticket` playbooks (prepare/connect-browser/capture-evidence/execute-change/closeout) | **AT-PAR (design) / BEHIND (deployed)** | We have the evidence-capture flow specced; we lack the autonomous ping→video→aggregated-evidence→one-gesture-merge loop wired end-to-end. |
| **CodePatch** | Slice a million-line codebase into ~50 feature sections, parallel review agents | Controller fan-out of reviewer workers; dimension-based parallel review (Workflow `parallel`/`pipeline`) | **AT-PAR / AHEAD (orchestration)** | CE's native fan-out + adversarial-verify patterns are arguably more sophisticated than his per-section split. One place we're genuinely not behind. |
| **OctoPool** | Token-pooling shim: route read-only calls through a GitHub App (15k/hr) to preserve personal token (5k/hr) | Per-dev GitHub Apps + OpenBao token custody + overwatch PAT | **PARTIAL / MISSING the pooling** | We already get App-tier rate via identities, but have **no rate-limit pooling/routing shim**. Not yet a felt constraint at our scale — flag for when parallel seats multiply. |
| **vision.md / AGENTS.md / SKILL.md** | Plain-text, agent-read policy: in/out-of-scope, invariants, review tuning. **Agents write their own** | `AGENTS.md` + `CLAUDE.md` + `governance/` schemas + `playbooks/` + `.claude/agents/` roles | **AHEAD (formalism) / over-engineered** | We have richer governed structure; we **lack** his plain-text simplicity AND the **"agents author/audit their own policy files"** self-improving pattern. |
| **Compounding tool-building loop** | Agents build tools that make the next agents better; "annoyance → automate"; it compounds | Doctrine `bake-gaps-into-ce-not-conventions`, SSOT, playbooks/runbooks — but aimed at *governance*, not throughput dev-tools | **BEHIND (the big one)** | We compound **governance substrate**, not **throughput multipliers**. We lack the ruthless annoyance→tool reflex that *is* his entire thesis. |
| **Triage → select → execute → verify → merge** | "What should I work on?" → pick 8 → agents run hours → AutoReview/Mantis verify → press merge | Conveyor (finder→dispatch→harvest→gate) + controller cron cycle | **AT-PAR (orchestration) / BEHIND (human-touch)** | Our loop exists and is well-run, but the **human touch per unit is far heavier**: controller dispatches each ticket + ratifies each PR. His human touch ≈ one merge gesture on aggregated evidence. |

---

## 2. The Two-Directional Gap

### (a) Where Peter is ahead of CE
1. **Throughput per operator** — 15k issues closed, 10–18 parallel sessions, "infinite tokens" mindset. We run ~3 seats and hand-drive them.
2. **The compounding tool-loop** — his core advantage. Each tool (CrabBox→Mantis, DiscCrawl→reports→triage) multiplies the next. CE's compounding is pointed at governance, not velocity.
3. **Ruthless loop-closing** — "any human touch-point is a failure to automate." We still *insert* human touch-points (per-ticket dispatch, per-PR approve) by default.
4. **Evidence-verified one-gesture merge** — he reduced the human to "watch the video, press merge." Our gate is a full controller review per PR.
5. **Deployed simplicity** — a GH Action + a `vision.md` closes 15k issues. Our equivalent (the belt) is more architected and not yet running.

### (b) Where CE is ahead / deliberately different
1. **Attestation (#289 SO_PEERCRED)** — cryptographic proof an action came from the real agent-in-container. Peter has none.
2. **The capability wall (#234/#239)** — merge requires a token *no contained agent can hold*. Structural, not behavioral, trust.
3. **Egress control + cred-brokering** — contained seats with zero raw creds; vault-sourced per-call identities. Peter's CrabBoxes are trusted VMs.
4. **Signed ratification + governed roles + schema** — auditable authority chains.
5. **The deployment×run-mode framework itself** — Peter has *no model* for team or skynet across trust boundaries. He **is** solo mode taken to its throughput limit.

### Thesis test — same goal or different?
**Different goals that look identical.** Peter optimizes **throughput-of-one-trusted-operator inside a single trust domain**. CE optimizes **governable delegation across trust boundaries** (multiple humans, contained agents, an external contributor like Nitzan today, untrusting customers tomorrow). 

Peter's model **does not generalize** to team/skynet-with-untrusted-parties — it has no answer for "how do two humans who don't fully trust each other, or a human who doesn't trust their agent, safely delegate the binding act?" That question is exactly CE's product. **So our governance is not over-engineering relative to our market — it's the market.** 

**The sharp finding:** we have been *paying the governance tax without yet harvesting the throughput that makes the protected thing worth protecting.* The moat is real; the castle is half-built.

---

## 3. The Real Autonomy Gap (yardstick: deployment × run-mode)

| | Dev (per-PR ratify) | CEO (policy-pre-delegated) | strangeLoop (near-full delegation + audit) |
|---|---|---|---|
| **solo** | — | **← Peter lives here** | Peter trends here |
| **team** | Nitzan (today, bridge) | (goal) | — |
| **skynet (us internally)** | **← CE lives here** | (goal — blocked on amortization, NOT on attestation) | — |

- **Peter sits in solo × CEO/strangeLoop.** He pre-decides scope (`vision.md`), delegates execution fully, and ratifies on aggregated evidence.
- **CE sits in skynet × Dev.** We have the *topology* of skynet (one operator → fleet) but operate it in the *heaviest run-mode* — the controller stands in as a per-PR human approver and per-ticket dispatcher.

**The dominant gap is (ii) trust/gate amortization — specifically run-mode, not (i) tooling.** Defense: even with infinite tooling, if every PR requires a per-item ratification gesture and every ticket a hand-dispatch, we never reach press-merge-on-aggregate autonomy. The binding constraint is that **we have not built the policy layer that lets the human pre-delegate classes of work and ratify on aggregated evidence.** Tooling (the compounding loop, AutoReview-auto, a running belt) is the strong *second* gap and is what *feeds* an amortized gate — but amortization is the lever. We own the safety mechanism (wall + brokers + attestation) to make CEO/strangeLoop *safe*; we simply have not shifted into that gear.

---

## 4. The Verdict the Operator Asked For

**Are #289 + #285 + team-mode the right next bets toward Steinberger-level autonomy?**

**Right investments, wrong priority order if the metric is throughput.** Here is the defensible position:

- **Peter proves attestation is NOT required for massive autonomy** — because single trust domain. So #289/#285 cannot be justified as "what unblocks Steinberger throughput." They don't. They are the **safety enabler for pushing the gate DOWN to contained/attested agents** — which only matters when (a) you want a contained agent to approve, or (b) you have parties who don't trust each other. Both are **team/skynet** concerns, not the solo-throughput concern.
- **Is our governance a moat or a tax?** **Both, and the sequencing is the whole answer.** It is a **moat** for our actual product (governable delegation across trust boundaries — the thing Peter structurally cannot sell). It is a **tax** the moment it is prioritized *ahead of* the throughput engine it exists to protect, because a moat around an empty castle just slows you down. We are currently in the tax regime: heavy gate, light engine.
- **Connect to doctrine:** the moat is **human-rooted ratification — irreducible but amortizable** via CEO/strangeLoop run-modes. We have built the *irreducible* part (the wall) and skipped the *amortizable* part (policy tiers + evidence-aggregation). Attestation (#289) makes amortization *safe across trust boundaries* — but you can amortize *within your own trust domain today* (auto-merge your own fleet's docs-only green PRs) with **zero attestation**, exactly as Peter does. **That is the unlock we're leaving on the table.**

**Bottom line:** Don't stop #289/#285 — they're the team-mode keystone and Nitzan + distributed approval need them. But **demote them from "the thing that gets us Steinberger autonomy" to "the thing that makes Steinberger autonomy safe to extend across trust boundaries."** The thing that *gets* us there is run-mode amortization + the compounding throughput loop. Build the engine; keep the moat advancing one step behind it.

---

## 5. Concrete Next Bets (sequenced)

### Throughput / amortization engine (lead — closes the dominant gap)
1. **CEO-mode policy-tiered auto-merge** *(net-new; THE top bet)* — pre-delegate low-risk classes (docs-only / green-all-gates / no-public-surface) to auto-merge with **no per-PR human gesture**; reserve a ratification gesture for high-risk classes (security, deps, public surface, governance). Converts our existing wall+merge-queue from **Dev → CEO mode**. Zero new attestation needed — it's within our own trust domain. *Highest leverage; this is the gear-shift.*
2. **AutoReview analog (self-triggering)** *(net-new wiring on existing parts)* — auto-fire a fresh-context reviewer-worker before a PR opens / pre-merge, encoded as **one line in AGENTS.md**, not controller-dispatched. We already have the `reviewer` role + `/code-review`. Steal his exact trigger pattern.
3. **Run the belt** *(existing: #218 belt-poller→daemon)* — get the ClawSweeper analog actually running as a daemon so tickets self-pick instead of controller-dispatch. This is the conveyor-autonomy we keep simulating by hand every cron cycle.
4. **Evidence-verified press-merge UX** *(net-new; Mantis analog)* — aggregate gate evidence (diff + test results + review notes + computer-use video where relevant) into a **single ratification surface** so the human's act collapses to "review the evidence bundle, press merge." Builds on the `computer-use-ticket` playbooks.
5. **Institutionalize annoyance→tool + agent-self-authored AGENTS.md** *(cultural + light tooling; cheapest, most compounding)* — make "felt friction → build the tool" a standing controller reflex, and let agents author/audit their own policy files. This is Peter's actual #1 habit and the source of all the rest.

### Governance moat (parallel track — one step behind the engine; team-mode enabler)
6. **#289 (SO_PEERCRED attestation) + #285 (socket durability)** *(existing)* — the keystone that makes pushing the gate down to contained/attested agents **safe**, and #285 the operational sibling (every broker restart strands a contained seat until it lands). Required for **distributed approval** and **Nitzan team-mode**. Keep advancing; do **not** let it gate the engine.
7. **Team-mode build** *(existing: #110 ClaudeCodeAdapter skeleton, #132 human-install, human-contributor schema role)* — Nitzan is the forcing function; this populates the **team** cell of the matrix and is the real external dogfood.

---

## Appendix — One-line steals from Peter, ranked by ROI for CE
1. *"Any human touch-point is a failure to automate."* → audit our conveyor for every place the controller inserts itself; default to policy.
2. *AutoReview as one line in AGENTS.md* → self-triggering review beats dispatched review.
3. *`vision.md` per project* → a dead-simple plain-text in/out-of-scope file the belt reads to auto-close — simpler than our schema, and it's what makes ClawSweeper work.
4. *"Agents write to the clanker the way the clanker writes to the clanker"* → stop hand-authoring agent policy files.
5. *"I have infinite tokens"* → our `dont-self-throttle-on-quota` doctrine already agrees; act on it for throughput, not just for finishing the arc.
