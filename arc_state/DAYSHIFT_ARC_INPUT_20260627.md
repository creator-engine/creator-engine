# Day-Shift Arc Input — CE-DEV-2 — 2026-06-27

> Compiled by read-only recon worker at session start. Primary sources: MORNING_20260627, NIGHTARC_20260626T2300Z, NIGHTARC_AUTONOMOUS_20260626T1830Z, CONTRIBUTOR_ONBOARDING_PLAN_20260627, tmp/27jun2026.md (lines 1050–1456). All live data verified against GitHub via overwatch token at compile time. No changes made.

---

## A. Night-Shift Arc — What It WAS

**Mandate:** Operator signed out ~18:30Z on 2026-06-26 granting full autonomous authority to drive the night-shift arc to completion. Scope: close the courier-retirement milestone, advance ARC 2 (rented-surface governance), and keep the conveyor draining.

**Operating model:**
- Hourly controller cron (`3b88e02c`, session-scoped, fires at :37) = judgment layer. Host crons (seat-check :00, belt-canary /5m, poll-devs :05, conveyor-tend :30) = durable backstop.
- All execution via Sonnet worker subagents; seats dispatched via prompt-pointer+SHA.
- Contained seats (dev-3, dev-4) briefed via `docker cp` into the container; controller holds gate + merge authority.
- Fleet-switch (push-side, dev-1/dev-4 → vault-sourced self-push) explicitly **PARKED** for Operator's return — gated on #285 (socket durability) + #289 (SO_PEERCRED attestation).

**The milestone (GATE β courier retirement):**
- Dev-3 was driven from-seat to self-push a real PR via the egress broker (ce-ops#287 → PR #548). Proven: vault-sourced App identity (`ce-forge-dev-3`), ephemeral per-call AppRole login to OpenBao, key never on disk or in the container, containment intact, broker audit logs show `decision=allow / pushed=true / pr=548`.
- **Honest gap logged at milestone:** broker does not log SO_PEERCRED — socket origin is not cryptographically attested (host spoofing not cryptographically ruled out). Filed as ce-ops#289 (SO_PEERCRED attestation, fleet-switch prerequisite).
- Autonomous cron stood down at ~01:44Z when Operator returned; gate was drained and the Operator continued the strategic morning session.

---

## B. Night-Shift Arc — What It Delivered (the Ledger)

### PRs Merged Since 17:00Z 2026-06-26

Verified live via `gh pr list --state merged`. **Total: 19 PRs** (checkpoint claimed "17"; live count is 19 — two earlier merges at 17:47Z and 17:59Z that pre-date the Operator sign-out were counted in the same shift).

| # | Merged | ce-ops ticket | What |
|---|--------|--------------|------|
| #535 | 19:58Z | #166 | Knowledge-SSOT slice-3 — self-identity probe + bootstrap drift-detect |
| #537 | 18:03Z | #146 | SSDF/SLSA conformance matrix |
| #541 | 17:50Z | #271 | Ring-1 toolchain self-update block + read-only VPS codex mount |
| #542 | 17:47Z | #282 | Contained-seat broker socket reachability + canonical self-review mount |
| #543 | 17:59Z | #281 | Per-policy commit-signature requirement (off for contained seats) |
| #545 | 18:00Z | #65  | CHANGELOG.md current to v0.2.0 |
| #546 | 19:58Z | #272 | Rented-surface manifest SSOT + completeness check |
| #547 | 20:50Z | #81  | ce-root-v1 trust-anchor fingerprint published via independent channels |
| #548 | 20:06Z | #287 | **Courier-retirement canary** — dev-3 self-push from-seat (vault-sourced, broker EPIPE fix) |
| #549 | 20:06Z | #110 | Ring-1 harness-adapter layer (ClaudeCodeAdapter skeleton) |
| #550 | 21:52Z | #286 | Persist --host-uds=open for gVisor runsc runtime |
| #551 | 20:53Z | #273 | surfaces_manifest_consistent CI guard (hard-fail) |
| #552 | 22:53Z | #274 | Digest-pin all Docker base images (4 Dockerfiles) |
| #553 | 22:53Z | #290 | Broker self-push PR-body work-class line injection |
| #554 | 22:53Z | #283 | Public-docs guard blocks net-new internal-only-tree files |
| #555 | 23:52Z | #288 | Count-agnostic registered-check assertions (kills serialization churn) |
| #556 | 01:50Z | #275 | Pin VPS runsc image tag by digest |
| #557 | 00:53Z | #276 | `ce surfaces check-updates` subcommand (read-only upstream detection) |
| #559 | 01:50Z | #147 | Identity-registry schema SSOT dimensions (emails/repos/cred-pointers/OpenBao integration) |

### ce-ops Issues Closed (Night Window — from Operator sign-out 18:30Z)

Live-verified from `gh issue list --state closed`:

**Since 18:30Z (autonomous night window):** 3 confirmed auto-closed via PR merge keyword:
- #272 closed 19:58Z — surfaces/manifest.yaml SSOT
- #283 closed 22:53Z — public-docs guard (internal-only tree block)
- #276 closed 00:53Z — ce surfaces check-updates

**Pre-sign-out (same shift, 17:00–18:30Z), including controller manual closures:**
- #282 closed 17:47Z — broker socket reachability
- #281 closed 17:59Z — per-policy commit-signature
- #271 closed 17:50Z — Ring-1 toolchain block
- #270 closed 17:47Z — canonical self-review mount variable
- #91 closed 18:06Z — agent-native operational docs (relocated per #249)
- #258 closed 16:36Z (just before window) — conveyor stranded-PR sweep
- #81 closed 20:50Z — trust-anchor fingerprint
- #110 closed 20:06Z — harness-adapter layer

**Total closed in the 17:00Z–morning window: 11.** The checkpoint claim of "11 ce-ops closed" is accurate when counting from 17:00Z (not the 18:30Z operator sign-out boundary).

**Important discrepancy noted:** Several PRs whose commit messages reference `Closes ce-ops#N` did NOT auto-close the ce-ops issue — this is by design (cross-repo `Closes` is a GitHub no-op; ce-ops#262's merge-triggered API close-bot handles it). As a result, the following ce-ops issues have merged PRs but remain OPEN in the tracker: **#273, #274, #275, #287, #288, #286, #290**. These are not open work — the code is merged — but the tracker needs cleanup or the close-bot to run.

### Net-New ce-ops Issues Opened Overnight (#285–#290)

All 6 opened during the night arc:

| # | Created | Status | One-line |
|---|---------|--------|---------|
| #285 | 18:11Z | OPEN (unstarted) | Egress broker sockets go stale on daemon restart — need systemd socket-activation |
| #286 | 18:21Z | OPEN (code merged in #550) | Persist --host-uds=open in deploy config |
| #287 | 18:21Z | OPEN (code merged in #548) | Broker BrokenPipeError on half-closed connection |
| #288 | 19:52Z | OPEN (code merged in #555) | Count-assertion brittleness serializes check-adding PRs |
| #289 | 19:53Z | OPEN (unstarted) | SO_PEERCRED attestation — prove seat-origin, block host spoofing |
| #290 | 20:46Z | OPEN (code merged in #553) | PR body omits Declared work class line → G5 gate fails every from-seat PR |

Note: #286, #287, #288, #290 all have merged PRs; the issues remain open in the tracker (same cross-repo close-bot gap as above). Only **#285 and #289** are genuinely unstarted.

---

## C. ARC 2 (Rented-Surface Governance) — Live Phase State

ARC 2 = serial chain on `surfaces/manifest.yaml`. Phases cannot fully parallelize (each adds capability others depend on).

### Phase 1 — FULLY MERGED

| Ticket | PR | Status | What |
|--------|----|--------|------|
| #271 | #541 | MERGED 17:50Z | Toolchain self-update block |
| #272 | #546 | MERGED 19:58Z | manifest.yaml SSOT + completeness check |
| #273 | #551 | MERGED 20:53Z | Consistency CI guard |
| #274 | #552 | MERGED 22:53Z | Digest-pin all Docker base images |
| #275 | #556 | MERGED 01:50Z | VPS floating-tag fix + digest pin |

All Phase 1 code is on main. Issue tracker shows #273/#274/#275 still OPEN (cross-repo close-bot gap, not real open work).

### Phase 2/3 — PARTIALLY MERGED

| Ticket | PR | Status | What |
|--------|----|--------|------|
| #276 | #557 | MERGED 00:53Z | `ce surfaces check-updates` (read-only upstream version detection) |
| #286 | #550 | MERGED 21:52Z | Persist --host-uds=open in deploy config |

### Phase 3/4 — IN FLIGHT / UNSTARTED

| Ticket | PR | Status | Hazard |
|--------|----|--------|--------|
| #277 | — | UNSTARTED | Carrier schema + SURFACE_UPDATE_RUNBOOK + validator check. **Check-adding risk**: hold until #288/#555 (count-agnostic) is confirmed merged+deployed (it is — #555 merged 23:52Z). Now unblocked. |
| #278 | — | UNSTARTED | `ce surfaces fleet-rollout` subcommand. Deps: #276 (MERGED) + #279 (in-flight). |
| #279 | #558 | **BLOCKED** — CI red | surfaces/render.py — manifest→build-args + launch-env.sh. Dev-3 is the author; CI shows `Validate governance artifacts → FAILURE`. REVIEW_REQUIRED. |
| #280 | — | UNSTARTED | Wire CI image build to source build-args from surfaces/render.py. Deps: #279. Touches `.github/**` → controller-only territory. |

**Sequencing note:** #277 is now safe to dispatch (#288/#555 merged). #278 waits for #279. #280 is `.github` territory, should be controller-driven or tightly scoped. The digest-pin test brittleness (hardcoded bare tags broke on digest — fixed in #556 by making tests digest-tolerant) is a resolved hazard but reviewers should check #279's test handling.

### #147 — MERGED (related to ARC 2 schema work)

#147 (identity-registry schema dimensions) merged in PR #559 at 01:50Z. Issue shows CLOSED in the tracker (auto-close worked — same-repo or the close-bot ran).

---

## D. The Keystone Work: #289 + #285

### ce-ops#289 — SO_PEERCRED Attestation

**Live state:** OPEN, unstarted. Filed 19:53Z night of 26 Jun.

**Why top priority per the gate doctrine (worked out in the morning strategic session, lines 1202–1251 of tmp/27jun2026.md):**

The morning session crystallized a fundamental reframe: **containment and authority are orthogonal axes that were accidentally welded together.** Attestation (#289) is the keystone that decouples them. Once an approval/action can be cryptographically proven to have come from the real attested agent inside a real container, a contained agent can safely hold delegated gate authority. Without it, a host process could spoof the seat. The fleet switch's "uncontained vs contained" framing was a roadmap artifact, not a principle.

#289 enables: (1) the push-side fleet switch to be safe (not just plausible), (2) contained agents to hold delegated approve authority once the broker's hard APPROVE-refusal is made policy-gated (not absolute), (3) the solo-dev product default (fully contained controller with the human as the gate) to be architecturally sound.

**Hazard:** touches broker daemon + potentially systemd socket handling. Should be controller-driven or dispatched to a tightly-scoped worker that understands the broker architecture. Not suitable for a blind contained seat.

### ce-ops#285 — Socket-Activation / Durability

**Live state:** OPEN, unstarted. Filed 18:11Z night of 26 Jun.

**Why top priority:** The broker incident during the night arc (EPIPE on the pre-#287 broker binary, broker crashed silently, dev-3 stranded for ~40 min) exposed that every broker restart strands any contained seat until a human intervenes. Systemd socket-activation removes that fragility: the socket survives daemon restarts, so a seat that sends to a temporarily-down broker doesn't lose its session. This is the operational prerequisite that makes the fleet-switch robust, not just proven-once.

**Hazard:** Same broker/systemd territory as #289. These two are natural co-dispatch or sequential work on the same files.

---

## E. Nitzan / Team-Mode BUILD Arc

### Bridge Status

**EXECUTED** (2026-06-27 morning). Nitzan94 (GitHub user id 219014518) has pending invitations:
- `creator-engine/creator-engine` — write (#323802094)
- `creator-engine/ce-ops` — read (#323802095)
- `creator-engine/docs` — write (#323802096)
- `creator-engine/ce-playbooks` — write (#323802097)

She is productive from the moment she accepts. Branch protection (CODEOWNERS review + require_last_push_approval + merge queue) enforces the hybrid gate automatically — she can push branches and open PRs but cannot self-merge.

**Governance model confirmed:** hybrid-iii now → hybrid-ii on graduation. Write + full review/comment immediately; approve-for-merge stays with gate (ce-dev-2 / Operator); graduates to CODEOWNERS peer human via trust-tier ladder in `docs/guide/contributing-to-ce.md`.

**ce-ops access:** day-one READ (Operator chose; she gets full internal context immediately).

Definitive plan at: `.ce/state/research/CONTRIBUTOR_ONBOARDING_PLAN_20260627.md`

### BUILD Arc — Proposed but NOT yet filed in ce-ops

These are candidate tickets, not yet created:

| Item | Depends on | Notes |
|------|-----------|-------|
| (a) Implement `ClaudeCodeAdapter` | #110 (MERGED — provides the skeleton) | #110 merged the harness-adapter layer but `ClaudeCodeAdapter` is a `NotImplementedError`. Nitzan's onboarding makes this the missing piece between the adapter layer and a human using CE with Claude Code. |
| (b) Human-install fixes | ce-ops#132 (OPEN) | #132 is already filed as the S1 installer blocker. The Nitzan BUILD arc folds into #132 — her onboarding is the human-must-work forcing function that elevates it from fleet-only to real product requirement. |
| (c) `human-contributor` role in identity schema | #137 (OPEN) | Current identity schema has no role for a human tied to a GitHub user (not a bot/seat). Minimal extension needed. Could be a child of #137 or #269. |
| (d) Trust-tier graduation criteria | — | Nitzan graduates to CODEOWNERS peer human when ready. The ladder exists in docs but the graduation criteria (N PRs landed, Operator confirmation) need formal encoding. |

**Status:** None of (a)/(c)/(d) are filed. (b) folds into #132. Controller should file these as a follow-up action before feeding them to seats.

---

## F. Open Loose Ends / Decisions Carried from the Night

1. **Fleet switch (push side) PARKED** — waiting on #289 (SO_PEERCRED) + #285 (socket durability). Do not execute autonomously. Have it queued for Operator one-word approval after those land.

2. **Broker-health check missing from cron backstop** — the broker crashed silently for ~40 min during the night arc; the seat-check cron (:00) did not detect it. Add a broker-health probe to the cron backstop. Not yet ticketed; should be filed and folded into #285 or as a standalone.

3. **Self-review canary never exercised from-seat** — the review broker is deployed, vault-wired, reachable, and verified healthy (daemon active, socket connectable from dev-3's container, APPROVE hard-refused by two independent guards). But dev-3 has never actually posted a COMMENT/REQUEST_CHANGES review through it from its own agent process. The canary (have dev-3 post a comment review on a non-self PR through the broker, capture audit evidence) is not yet run. Until it is, self-review is "deployed but unproven."

4. **PR #558 (dev-3, ce-ops#279) — BLOCKED** — CI red (`Validate governance artifacts → FAILURE`), `REVIEW_REQUIRED`. Dev-3 was mid-fix as of the morning checkpoint. Current state: the PR is still open and blocked. Needs dev-3 to push a fix and the controller to re-review + enqueue.

5. **#290, #286, #287, #288 tracker cleanup** — ce-ops issues that have merged PRs but remain OPEN in the tracker (cross-repo `Closes` keyword no-op). The close-bot (#262) should handle these, or controller should manually close them.

6. **Conveyor — dev-1 and dev-4 IDLE** — both were held (not auto-fed) with Operator returning. dev-1 at ~82% context, dev-4 at ~88%. Ready to re-feed when the day-shift arc is sequenced.

7. **ce-ops#132 (release-artifact parity)** — open, no in-flight PR. Should route to dev-1 per the night checkpoint. Now also the install-readiness gate for the Nitzan BUILD arc.

8. **ce-ops#269 (internal real-value identity registry)** — OPEN, no in-flight work. Nitzan's formal registry entry will land here eventually; not a day-one blocker.

9. **Peter Steinberger analysis** — the immediate next action per MORNING_20260627.md. Transcript at `tmp/peter_steinberger_msbuild_transcript.txt` (6,656 words). Goal: mine against CE's current setup using the deployment×run-mode model + gate doctrine as the measuring stick. This is the Operator's stated first move on resume.

---

## G. Seat State (Best-Available Read — Cannot See Live Panes)

| Seat | Best-known state (from morning checkpoint) | Context % | Notes |
|------|--------------------------------------------|-----------|-------|
| **dev-1** | Idle — was fixing #556 (digest-tolerant launcher tests); #556 merged at 01:50Z so that work is done | ~82% | Non-contained VPS codex; tmux `ce-dev1-orchestrator` pane %2; self-push as ce-dev-1. HELD — not auto-fed. Ready to pick up new work. Good candidate for #132 (install), #277 (ARC 2 carrier schema). |
| **dev-3** | Working on ce-ops#279 / PR #558 (mid-fix as of ~02:00Z) | ~72% (last known) | Contained `ce-vps-codex` on VPS; herdr w1:p1; self-push via broker (proven). PR #558 is still BLOCKED/CI-red. Dev-3 may have pushed additional commits since last check — verify. |
| **dev-4** | Idle — #147/#559 merged; reset to fresh | ~88% (last known, approaching fresh) | Contained `ce-dgx-codex` on DGX; herdr w1:p1; commit-only (controller intake-pushes). HELD. Good candidate for schema work, #277, or Nitzan BUILD arc items. |

**Note:** These are checkpoint-derived snapshots. Live pane state is not verified in this recon. Do not dispatch without probing.

---

## H. Candidate Day-Shift Work-Pool (Bucketed)

### Bucket 1: Governance Keystone + Fleet Switch
**Priority: TOP (blocks the unified delegation model)**

| Item | Size | Blocking dep |
|------|------|-------------|
| ce-ops#289 — SO_PEERCRED attestation | Medium (broker code + audit logging) | None — unstarted |
| ce-ops#285 — systemd socket-activation | Medium (systemd unit + broker startup change) | None — unstarted; natural co-work with #289 |
| Fleet switch (push side, dev-1/dev-4) | Small (config + test) | #289 + #285 must land first; one-word Operator approval needed |
| Broker-health cron probe | Small | Can fold into #285 or standalone |
| Self-review canary (prove from-seat comment/REQUEST_CHANGES) | Small | Broker healthy (verified); just run the canary |

**Total bucket size:** ~2–3 medium PRs + a few small items. Both #285 and #289 touch broker/systemd — controller-driven or tightly scoped dispatch (not a blind contained seat).

---

### Bucket 2: ARC 2 Completion (#277/#278/#279/#280)
**Priority: HIGH (in flight; #279 blocking #278/#280)**

| Item | Size | Blocking dep | Assignability |
|------|------|-------------|--------------|
| ce-ops#279 (#558 fix) | Small (CI fix dev-3 is already on) | None — dev-3 mid-fix | Dev-3 self-push |
| ce-ops#277 — carrier schema + runbook + validator | Medium | #288/#555 MERGED (unblocked now) | Any seat; check-adding hazard resolved |
| ce-ops#278 — fleet-rollout subcommand | Medium | #276 (merged) + #279 (in-flight) | dev-1 candidate after #279 |
| ce-ops#280 — wire CI image build to render.py | Small-Medium | #279 | `.github/**` territory → controller-only or single-file dispatch |

**Total bucket size:** 3 medium PRs + 1 blocked. After #279 unblocks, #278 and #280 can be dispatched. #280 touches `.github` and warrants controller supervision.

---

### Bucket 3: Nitzan Team-Mode BUILD Arc
**Priority: MEDIUM (new; must file tickets first)**

| Item | Size | Notes |
|------|------|-------|
| File the 4 BUILD arc tickets (a)/(b)/(c)/(d) | Tiny — controller action | (b) folds into #132; (a)/(c)/(d) are net-new |
| Implement `ClaudeCodeAdapter` | Medium | Depends on #110 (merged); core product work |
| #132 — human-install S1 fixes | Medium-Large | Already filed; route to dev-1; the Nitzan forcing function |
| `human-contributor` role in identity schema | Small | Extends #137/#269; can be a child ticket |
| Trust-tier graduation criteria | Small | Docs-level; Nitzan-specific |

**Total bucket size:** 1 large (#132), 2 medium, 2 small. Filing the tickets is the immediate prerequisite. #132 is the critical-path gating item for Nitzan's productive CE deployment.

---

### Bucket 4: Throughput / Tooling (Placeholder — Peter Analysis Feeds This)
**Priority: TBD — run Peter analysis first**

The immediate next action per the morning checkpoint is mining the Peter Steinberger MS Build transcript (`tmp/peter_steinberger_msbuild_transcript.txt`) against CE's current setup using the deployment×run-mode model as the measuring stick. This analysis is expected to surface autonomy gaps and may generate new work items here. **Hold this bucket until the Peter analysis is done.**

Known placeholder items:
- Conveyor re-feed (dev-1/dev-4 idle) — ready once the arc is sequenced
- ce-ops#269 internal identity registry — no in-flight work; not blocked

---

### Bucket 5: Loose-End Hygiene
**Priority: LOW-MEDIUM (but some are quick wins)**

| Item | Size | Notes |
|------|------|-------|
| Close tracker drift (#286/#287/#288/#290/#273/#274/#275) | Tiny | Manual gh issue close or wait for close-bot; these are code-merged, issue-open |
| Broker-health cron probe | Small | Should be folded into #285 scope |
| Self-review canary | Small | Quick; dev-3 agent fires a COMMENT review via the review broker against another seat's PR; captures audit evidence |
| #558 re-review after dev-3 fix | Tiny | Gate action; controller approves + enqueues when CI goes green |
| Nitzan day-one packet | Tiny | Draft welcome message with invite links + CONTRIBUTING/contributing-to-ce/ce-playbooks orientation |

---

## Summary Matrix

| Bucket | Size | Key Blocker | First Action |
|--------|------|------------|-------------|
| 1. Governance keystone | 2–3 PRs medium | None | Dispatch #285+#289 (co-dispatch or sequential; controller/scoped) |
| 2. ARC 2 completion | 3 PRs medium + 1 in-flight | #279 must close before #278/#280 | Verify dev-3 #558 fix; dispatch #277 to dev-1 (now safe) |
| 3. Nitzan BUILD arc | 1 large + 2 medium | File tickets first | File (a)/(c)/(d) in ce-ops; route #132 to dev-1 |
| 4. Throughput/tooling | TBD | Peter analysis | Run Peter Steinberger analysis first |
| 5. Hygiene | 5 small items | None | Close tracker drift; run self-review canary |

---

*Compiled by recon worker 2026-06-27. Sources: live gh data (PRs, issues) + 4 checkpoint docs + strategic session transcript. No changes made to any CE artifact.*
