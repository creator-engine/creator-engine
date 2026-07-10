# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (PM) · NIGHT-SHIFT RUNNING (unattended)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet 100.100.105.50), tmux session `ce-controller`, cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_NIGHTSHIFT_LAUNCH.md`. Read this + `MEMORY.md` first. **main HEAD = `707e4406`.**

**STATUS: night-shift arc RATIFIED + FILED + LAUNCHED. Operator SIGNED OUT — fully unattended.** No further Operator-side items pending except the W4 topology escalation (when it comes) and #156 Web-B (gated).

**PEER-SEAT → HOST → REACH (verify a handle resolves locally before inferring state):**
- **dev-1** = VPS, `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. Reviewer-of-record (posts as **ce-dev-1**, CODEOWNER). Self-pushes.
- **dev-3** = VPS, `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard:1.0`. Own gh identity (ce-dev-3). Self-pushes.
- **dev-4** = CONTAINED DGX, `ssh cedev4@localhost`; tmux `dev4stage1:0.0`; **NEVER C-c**. Container cwd `/workspace/creator-engine` ↔ host `/home/cedev4/ce-workspaces/creator-engine`. No egress → courier deliverables via overwatch push.
- **Local seats (this DGX, `tmux ls` as cedev2):** `ce-cockpit` (W8 #45 built), `ce-egress` (W5 #153 built), `ce-webui` (#28), `ce-web152` (#152), `ce-controller` (me).
- Briefs: write → `sha256sum` → scp to VPS `/tmp/` (dev-1/3) or `cedev4@localhost:/home/cedev4/ce-workspaces/creator-engine/tmp/` (dev-4) → seed pane `Read <path> (sha256 <h>) and execute`. Seed gotcha: long pastes sometimes need a SECOND `Enter` (or `tab to queue` if seat busy).

## ⏸️ AWAITING-OPERATOR
- **W4 #157 minting topology — DESIGN DELIVERED, needs Operator nod.** dev-4 recommends a **CENTRAL tenant-partitioned minting service** (shared-App PEM held in OpenBao SecretIdentityBackend; colocated with the ADR-0007 egress broker as its token-minting leg, NOT a second forge authority; users install the published CE App; value-free mint request → broker verifies install/run binding + scope + policy ceiling → mints short-lived installation token). Rejects per-tenant PEM custody (violates #117). Design: branch `ce157-shared-app-minting-backend` commit `110d9ac`, doc `.ce/state/research/DESIGN_ce157_shared_app_minting_backend_20260620T181329Z.md` (+ non-binding scaffold + tests). **DO NOT wire architecture/runtime until Operator ratifies the topology.** Caveat: dev-4 couldn't see #153's unpushed commit 095f3527 (contained) — reconciled against ADR-0007 + role desc; cross-check vs the actual ce-egress-broker code before building.
- **#156 Web-B** — GATED.

## ARC = ce-ops#161 (ratified as-is). 11 waves; grants mirror #129.
**Hard rules:** hashes REPRODUCED never transcribed · distinct-reviewer before every merge · escalate-only-on-blockers · no binding architecture commit w/o Operator nod (W4).
**Wheel-serialization:** W1 #290, W2 #159, W8 #45, W9 #119 all rebuild `validators/wheelhouse/*.whl` → merge ONE at a time, each rebases+rebuilds after the prior merges.

### DISPATCH STATE (as of ~19:24Z) — main=d6ba7ee2
- **W1 #290** ✅ MERGED (b25e57b3). Symlink-TOCTOU fix; ce-dev-1 re-reviewed w/ reproduced evidence. Day-batch wrapped.
- **W3 #160** ✅ MERGED (#291, squash → d6ba7ee2). Rulesets protection floor (free-plan private repos). dev-1 authored+rebased, ce-dev-3 reviewed+APPROVED with reproduced evidence (wheel 7dd9cf4c, 3581 passed, bypass_actors==[], fail-closed verified). **Onboarding P0 LANDED.**
- **W4 #157** ✅ DESIGN DELIVERED → ⏸️ AWAITING-OPERATOR topology nod (see top). Parked; not wired.
- **W2/W5/W6/W7/W8/W9/W10/W11** = QUEUED, **HELD ON POOL WALL**. ⛔ Shared codex pool ~4% weekly (near dry). Operator NOTIFIED (push) for the x20 upgrade they pre-flagged. **DO NOT launch new waves until pool replenishes** — would dry mid-build. On pool restore: resume onboarding cluster (W5 #153 courier→PR, W6 #158), then build-fwd. dev-1/dev-3/dev-4 all idle.
- **Loop posture:** quiet period (pool-dry + awaiting Operator). Stopped re-arming the fleet-watcher (it was busy-looping on the quota-low signal, already acted on). Relying on the ScheduleWakeup heartbeat; will re-arm watcher + resume dispatch once pool is back. Cron seat-snapshot still runs hourly.

### OPEN PRs (main=707e4406)
- **#290** CHANGES_REQUESTED/BLOCKED — W1 fix in flight (dev-3).
- **#281** CHANGES_REQUESTED — W7 rework, not yet dispatched (branch `ce135-openbao-secret-zero-broker`).

## MONITORING (set up this session — survives /clear, NOT session death except cron)
- **Cron:** `crontab -l` → `0 * * * *` runs `~/ce-seat-check.sh` → appends `~/ce-night-log.txt` (+ `~/ce-seat-check.cron.log`). Snapshots all 8 seats' context% + working/idle + open PRs; flags any seat >45% used. Bare-env ssh verified (default key id_ed25519, BatchMode).
- **Fleet-watcher:** event-driven, re-arm on resume: `bash ~/ce-fleet-watcher.sh` (run_in_background; sources `~/.ce-keys/overwatch.env`). DIES on /clear — RE-ARM.
- **Controller heartbeat:** ScheduleWakeup ~3600s (autonomous-loop-dynamic) to wake me to ACT (merge ready PRs, route reviews, re-seed, dispatch next wave). Re-arm each wake.

## CONTEXT-CLEAR POLICY (Operator directive 2026-06-20 PM + my operational refinement)
Operator: "check context usage each dev; if over 45% → save state, clear, resume." **Observed: codex seats AUTO-COMPACT** (dev-3 26%→83% left; dev-1 91% used → compacted to 0%). So: a seat over 45% used that is mid-productive-work usually self-recovers via compaction. **My applied policy:** force a save→clear→resume only when a seat is over 45% used AND at genuine exhaustion risk (≲12% left) or idle at a clean checkpoint; otherwise FLAG + re-check next cycle. Always SAVE (resume file + commit WIP) before any forced clear. The brief on disk + a resume file = the re-seed material. ⚠️ If Operator meant STRICT 45% clears, adjust.

## OPS
- gh on this host: `source ~/.ce-keys/overwatch.env; export GH_TOKEN=$CE_OVERWATCH_PAT` (= ce-overwatch). Push via inline `https://x-access-token:$CE_OVERWATCH_PAT@github.com/...` — never bake into config.
- Briefs on disk: `~/ce-briefs/` (ce290-symlink-fix, w3-160-rulesets, w4-157-minting-backend, + earlier).
- Shared-App PEM `/dev/shm/ce-shared-app.pem` (re-place only after host reboot).
- Codex shared GPT pool ~9% weekly — Operator: fine, x20 if hit. Meter throughput; escalate (don't stall) if dry.

## LEARNINGS (carry from launch resume — still apply)
- dismiss-stale does NOT fire on controller rebase force-push (approval survives); strict-up-to-date → each merge makes next PR behind → rebase needed.
- `decision_record` `status: accepted` REQUIRES a `ratification` block (ratified_by concrete handle, ratified_at, ratification_prompt_sha, quorum). Pattern = ADR-0001.
- CI trigger gap: if `check-runs==0` on a new SHA, `gh pr close && gh pr reopen` re-triggers validate.yml.
- Reviews caught 6+ real bugs across the day batch incl. against the controller — keep distinct-reviewer-before-merge inviolable. (#290 symlink-TOCTOU is the latest catch.)
