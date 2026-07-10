# RESUME STATE — CE-DEV-2 Controller · 2026-06-21 · COMPANY-BRAIN + WORK-SIZING + #161 WRAP

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet 100.100.105.50), tmux `ce-controller`, cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_NIGHTSHIFT_RUNNING.md`. Read this + `MEMORY.md` first. **main = `fab49ddc`** (#293). Full session transcript saved: `.ce/state/research/TRANSCRIPT_CE_DEV2_20260621_companybrain-worksizing-foreman.jsonl` (sha 52bf2985…, both hosts).

**PEER-SEAT → HOST → REACH (verify a handle resolves locally before inferring state):**
- **dev-1** = VPS `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. Self-pushes as ce-dev-1.
- **dev-3** = VPS `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard:1.0`. Self-pushes as ce-dev-3.
- **dev-4** = CONTAINED DGX `ssh cedev4@localhost`; tmux `dev4stage1:0.0`; NEVER C-c. Container cwd `/workspace/creator-engine` ↔ host `/home/cedev4/ce-workspaces/creator-engine`. No egress → courier via git-bundle (bundle on dev-4 → shared /tmp → fetch on cedev2 → overwatch push; keeps token OFF the seat).
- Brief dispatch = write file → sha256 → scp to seat /tmp (dev-1/3) or container tmp/ (dev-4) → seed `Read <path> (sha256 <h>) and execute`. Long paste often needs a 2nd Enter; busy seat → Tab to queue. **⚠️ NEVER inline `$CE_OVERWATCH_PAT` in a seed (remote shell empties it → broke a #167 dispatch); seats use their OWN gh auth.**
- **CODEX SEATS HAVE NATIVE FAN-OUT** = `multi_agent_v1` (explorer/worker roles). dev-4 confirmed. They CAN operate as foremen NOW (earlier "codex lacks fan-out" was WRONG, corrected in memory).

## ⏸️ AWAITING-OPERATOR — NOTHING BLOCKING
All major decisions ratified this session. Remaining (non-blocking, future): work-sizing F2 enforcement-location ADR (written at F1-build, ce-ops#168 Q1); company-brain Phase-2/3 (Graphiti/Mem0) deferred per research.

## RE-ARM ON RESUME (watcher dies on /clear)
`bash ~/ce-fleet-watcher.sh` (run_in_background; sources `~/.ce-keys/overwatch.env`). gh ops: `source ~/.ce-keys/overwatch.env; export GH_TOKEN=$CE_OVERWATCH_PAT`.

## IN-FLIGHT SEATS (as of session end)
- **dev-1** → building **#167** (company-brain SSOT assertion-ledger slice — Operator-prioritized) → THEN review queue: PR #292 (after dev-3 rebases) + PR #295 (ADR-0009, quick).
- **dev-3** → was CONTEXT-ROTATED (resuming from its newest RESUME_STATE). Queued 3 tasks: (1) rebase its own PR #292 (egress, BEHIND main, keep the 2 bug-fixes), (2) review PR #294 (W6), (3) review PR #281 (W7). ⚠️ dev-3 is the SOLE distinct reviewer for dev-1/dev-4-authored PRs (dev-4 contained can't post) = the review bottleneck.
- **dev-4** → building **#168 / F1** (work-sizing `size_ceremony` pure fn + schema). Also has BUILT-uncouriered: **W9 #119** (branch ce119-tasks-handoff-validator) and **W4 #157** (branch ce157-shared-app-minting-backend, depends on #153/#292). Courier both when free.

## OPEN PRs (main=fab49ddc) — drive these to merge first on resume
- **#294** W6 trust-anchor (author dev-4, rebased dev-1) → ce-dev-3 review → merge. Wheel-touching.
- **#292** W5 egress (author dev-3) → BEHIND, dev-3 rebase → ce-dev-1 review → merge. No wheelhouse. #157/W4 depends on it.
- **#281** W7 OpenBao rework (author dev-1) → ce-dev-3 review → merge. Wheel-touching.
- **#295** ADR-0009 bounded-work-units (docs) → any distinct review → merge. No wheel.

## MERGED THIS ARC (#161): #290 (Ring-1 symlink fix) · #291 (Rulesets P0) · #293 (scanner-pins P0). Earlier AM/PM: #275/#280/#282/#283/#284/#285/#286/#287/#288/#289.

## NEW PROGRAMS + TICKETS THIS SESSION (the "deterministic > probabilistic" doctrine thread)
The whole session converged on ONE meta-principle: move behavior/bounds/knowledge OUT of the probabilistic agent INTO CE's deterministic layer. Tickets:
- **#165** (PARENT tenet) **bounded work-units** → ADR-0009 (=PR #295). Children: **#163** foreman delegation (deterministically enforced — seat_class foreman/worker, Gate B/C, action-type×irreversibility metric; design on #163; defaults RATIFIED sha 6567380f), **#164** small-PR/merge-queue (kill rebase-hell + wheel-serialization; evidence-grounded ~200/400 lines).
- **#166** (PARENT) **CE Knowledge SSOT** (deterministic, independently-checked, capabilities PROBED-not-remembered, supersedes flat-file MEMORY.md for shared facts). Child: **#162** SSOT ops-docs runbook. Sibling **#91**.
- **#79 COMPANY BRAIN** (Operator-prioritized) — design FINALIZED + RATIFIED (sha e803962…). Two layers behind 1 MCP surface: deterministic **Knowledge-SSOT** (CE-native on evidence-spine, no datastore — the priority half, satisfies #166) + probabilistic **recall** (txtai laptop-MVP → Cognee/PG at scale, behind a CE recall ADAPTER). Naming = **"brain origin"** role (NOT "CE-DEV-1"). Recall default for teams = SHARED on the git brain-origin (solo=local/team=git-shared/scale=server). MEMORY.md migration additive/gradual (#162 first domain). First slice = **#167** (assertion ledger, building on dev-1).
- **#168 / F1** work-sizing engine spine = `size_ceremony(work_class, mutation_class)→artifact_set` pure fn (size→decomposition+conveyor; risk→ratification-gates+ADR; INDEPENDENT axes). RATIFIED sha c323eb4…. Design on **#45** (journey-cockpit UX) + engine under #165. F2 (classifier+floor) GATED on #164's grounded thresholds. Building on dev-4.
- The **SDLC-intake/work-sizing journey** = how CE auto-scales PRD→SDD→epic→decomposition proportional to consequence; builds on existing Spec-Kit + tasks_handoff(#119); design on #45.

## NEXT MOVES ON RESUME (priority order)
1. Re-arm watcher.
2. Drive the review pipeline → merges: dev-3 reviews #294/#281 + rebases #292; dev-1 reviews #292/#295. Merge each on APPROVE+green (overwatch, squash, wheel-serialize the wheel ones one-at-a-time).
3. Courier dev-4's built W9 (#119) + W4 (#157, after #292/#153 merges so it rebases onto merged egress).
4. Dispatch remaining #161: W8 (#45 cockpit, branch ce45 on origin, needs rebase + GOVERNANCE review), W10 (#155 Web-A), W11 (#151/#148). Per Operator priority, #167 (brain) + #168 (work-sizing) rank ahead of W8/W10/W11.
5. Monitor #167 + #168 builds → courier/review/merge.

## LEARNINGS THIS SESSION (apply)
- **Review-pipeline stalls when a seat context-rotates** — dev-3 rotated and SILENTLY DROPPED its queued reviews (#294/#292) → PRs sat. Queues don't survive rotation. This IS the merge-queue (#164/#165) + reviewer-triage (#120) problem; babysit reviews until built.
- **Reviewer bottleneck:** dev-3 is the only seat that can post reviews for dev-1/dev-4-authored PRs (dev-4 contained can't post; author≠reviewer). Distribute by AUTHOR.
- **codex multi_agent_v1 exists** — seats can foreman now (interim, prompt-propagated; durable = #163 born-a-foreman). dev-1/dev-3 sent confirm+directive (pending their yes/no).
- **Don't self-throttle on quota** (Operator directive) — push, let the hard limit stop you. Pool now x20 (~97-99% weekly).
- **Wheel-serialization tax** persists until ADR-0006 controller-bakes-wheel (#164) — wheel PRs (#294/#281/W9/W4/W8) merge one-at-a-time with rebase.
- **Ratification block** (decision_record, status:accepted) needs ratified_by(concrete)/ratified_at/ratification_prompt_sha/quorum — anchors saved in `~/ce-briefs/ratification-2026*.txt`.

## OPS
- Briefs/ratification anchors: `~/ce-briefs/`. Shared-App PEM `/dev/shm` (re-place after reboot only).
- MEMORY.md OVER BUDGET (37KB+) — prune/condense index lines when adding; the #166 brain is the eventual fix.
- Memories written this session: ce-dont-self-throttle-on-quota, ce-single-source-of-truth-ops-docs, ce-controller-spawns-many-workers (+codex-fan-out correction), ce-bounded-workunits-tenet, ce-knowledge-ssot.
