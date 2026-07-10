# RESUME STATE — CE-DEV-2 — 2026-07-08 midday — DAY-ARC-2 RUNNING (post-dispatch checkpoint)

> READ ORDER: MEMORY.md → DECISIONS_20260708.md (NOW 11 items — decision 11 = Q2
> RATIFIED: dedicated narrow App for materializer) → this file. Supersedes
> RESUME_STATE_CE_DEV2_DAYARC2_20260708.md (its lane definitions still valid).
> RULES unchanged: no `model` on pinned-role spawns; reviewer baseline=merge-base;
> ctx>45%=/clear; herdr drive = IN-CONTAINER wrapper (MEMORY.md line updated today —
> `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock
> <container> herdr agent send|pane read|pane send-keys` — bare host herdr / in-container
> tmux DO NOT EXIST).

## DONE THIS SESSION (verify, don't redo)
1. Board checked: empty at main 010ef3de. All 3 seat READY markers were STALE
   (ce-888→#894, ce-491→#889, ce-891→#893 all MERGED). Nothing was pending harvest.
2. Watchers armed fresh in .ce/state/watchers/*-20260708.sh: board-watch (bg),
   seat-watch (bg, dedup file seat-signal-20260708.seen pre-seeded with the 3 stale
   markers), c5-watch (bg). Prior night c5 watcher closed 60m clean.
3. ce-ops#184 EXECUTED + evidence commented (issue was already closed): VPS now has
   8G swapfile (fstab-persisted) + /tmp tmpfs capped 16G→8G (live remount +
   /etc/systemd/system/tmp.mount.d/ce-184-size.conf); 1d age policy pre-existed.
4. Q2 registry check done → Operator ratified "dedicated narrow App" → DECISION 11
   appended to DECISIONS_20260708.md, dual-written. Option A slice 1 dispatchable
   AFTER ce-iac-singleton-redeploy lands (decision 1 precondition).
5. INTAKE BATCH DISPATCHED (file+SHA pointers verified byte-equal; all 3 seats
   confirmed Working; claims in .ce/claims/ce-dayarc2-intake-20260708.md):
   - dev-4 ← ce-482-broker-v1-slice1 (broker v1 slice 1; commit-only; brief
     .ce/briefs/BRIEF_dev4_482_broker_slice1_20260708.md sha 360e723d…)
   - dev-3 ← ce-499-seat-ready-profile (seat-ready validate-pr profile;
     commit-for-harvest; brief BRIEF_dev3_499_seat_ready_20260708.md sha ccae2737…)
   - dev-1 ← 2 units self-push: ce-iac-singleton-redeploy (U1) +
     ce-ring1-launch-provenance (U2); brief BRIEF_dev1_iac_ring1_20260708.md
     sha 3efad39b…
6. Main-lineage worktree for reading designs: .ce/wt-dayarc2-main @ 010ef3de.

## FINDINGS
- Codex standby controller session (tmux ce-controller) is GONE on this host —
  needs canonical relaunch (+ ce-ops#502 fix still open).
- dev-3/dev-4 codex context: ~72% left each — fine for one unit, watch on re-brief.

## NEXT MOVES (in order)
1. Watch for READY/BLOCKED signals + board changes (watchers will fire; harvest
   dev-3/dev-4 via harvest_intake worker; dev-1 self-pushes → gate reviews).
2. Controller-direct: A-1 Arad workflow-refresh apply staging via App lane
   (authorized, decision 5; ARAD_SEND_READINESS_20260707.md).
3. Controller-direct: A-5 0.3.4 cut staging off CURRENT main incl. signing
   (decisions 6+9; RELEASE_0_3_4_CANDIDATES_20260708.md; release playbook;
   verify merge-base vs current main — root checkout lineage rc2 is STALE).
4. Ring-1 smoke after dev-1's U2 merges (decision 4b): live governed
   `ce launch --harness codex` → evidence packet → reassemble RING1_PROMOTION_PACKET.
5. Next intake wave when seats free: fleet-parity units (dev-3 image
   rebuild+ssh-keygen, dev-4 egress-broker deploy on DGX, self-push canaries),
   then Option A slice 1 (all 4 Qs now ruled) once IaC unit lands.
6. Relaunch codex standby controller canonically.

## ⏸️ AWAITING-OPERATOR (now 2!)
1. Arad T4 pack + md-sources decision (apply+send otherwise ready).
2. Nitzan D6 answers (their timebox) + Ring-1 flip (returns WITH smoke evidence).
