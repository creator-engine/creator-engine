# RESUME STATE — CE-DEV-2 — 2026-07-09 13:45 UTC — STRANGELOOP1D (post-DGX-reboot recovery)

> Delta over STRANGELOOP1C (read 1B+1C first). DGX HOST REBOOTED 12:54 → factory-down incident,
> recovered by 13:40. Controller dark gap #2 (~07:45→13:13). Full incident in ledger 13:13 entry.

## BOARD (13:45)
- MERGED this arc: 12 (#905-#911, #913-#917). Open: #912 (Operator-held) · #918 (hermes, fix
  worker resumed — B1 drop committed READY + M1 STATE_PATH_GUIDANCE) · #919 (ce-501 canary,
  review running, LIVE-GATE-SURFACE lens) · #920 (ce-502 standby, review running, AUTHORITY lens).
- dev-1: self-pushed #919+#920 DURING controller-dark gap (self-push value proven). Idle at 60%
  left — restock after its PRs clear review (fold-backs may need it).
- dev-3: ce-504-broker-arming-blockers READY (harvest worker resumed, handles it + 515/516;
  MUST drop committed .ce/wt-504/READY file — brief-template defect). Working/idle at ~53% left.
- dev-4: container recovered from reboot (config toml regenerated at /tmp/creator-engine-dgx-
  runsc-codex-config-1002-cedev4.toml — sed-edit only, fs.protected_regular blocks root rewrites;
  stale gVisor filestore MOVED to /home/cedev2/.ce/dev4-crash-recovery-20260709/gvisor.overlay.img
  [90GB, contains git bundles of lost WIP — carve scan bundle-offsets.txt running]). Batch
  re-dispatched from scratch (ce-493/492/461, sha f3116b95… re-verified). Prior WIP lost.
- Gate: systemd, survived reboot (active). Host crontab intact (watchdog */10 still runs —
  REMOVE at arc end).

## WORKERS IN FLIGHT (all resumed post-crash via SendMessage — transcripts under
/tmp/claude-1003/-home-cedev2-creator-engine/*/tasks/)
1. #918 fix (B1+M1) → push → then I approve; on merge: Unit C resume (1B prescription, ratchet
   103→104) + #500 remaining slices re-target + ce-453 Part A unblocks.
2. dev-3 triple harvest (515, 516, 504) → 3 PRs → reviews.
3. Backlog-hygiene ticket (stale-open already-landed class; evidence #473/#459/#500/#453).
4. Reviews #919 + #920 → mechanical fixes at harvest, judgment → dev-1.
- Session cron RE-CREATED (21,51 * * * * dev check — note 7-day expiry). Fleet signal watcher
  armed. 25-min heartbeat NOT re-armed (fleet watcher + cron cover it).

## ⏸️ AWAITING-OPERATOR — unchanged queue (1B §list) PLUS:
- STRANGELOOP-2 mandate items now URGENT per Operator 13:40 directive: (a) controller→VPS
  migration plan; (b) IaC-spawnable controller + SSOT-fed state (accelerates #496/#498; today's
  reboot = the evidence). Controller to draft the migration/acceleration proposal for
  ratification as part of arc close.

## GOTCHAS LEARNED THIS INCIDENT
- Launcher config toml lives in /tmp → host reboot bricks `docker start` (bind source missing).
  Regen from run-codex-runsc.sh template lines 287-315; hook command value = UNQUOTED env values.
  fs.protected_regular: root cannot rewrite others' /tmp files — use sed -i (rename-based).
- Stale .gvisor.overlay.img.<cid> in overlay2 diff dir blocks container start after unclean
  shutdown; the img IS the container's runtime fs (self medium) — mv it aside (preserves data,
  unblocks start). Seat WIP lives ONLY there → commit-early doctrine is load-bearing.
- On dev-4 restart the codex TUI needs NO re-auth (mounted CODEX_HOME) but pane starts fresh
  (/new context); worktrees+briefs in /var/tmp are GONE — re-stream brief, re-dispatch.
