# DIAGNOSIS + FIX DESIGN — VPS storage-fill class + gate outage — 2026-07-10
# Author: supervising (read-only) controller session on DGX, per Operator directive:
# diagnosis/design here, EXECUTION by the main VPS controller. Hand-off: implement as
# STRANGELOOP-2 units; F-1/F-2 ahead of the pending harvest wave.

## A. Incident chain (evidence-grounded, times UTC)

1. **Root disk hit 100% (0 bytes free)** — third storage-fill on this host in ~36h
   (prior: two 100%-root incidents cited in N-6 mandate evidence).
2. **Merge gate crashlooped 05:24→05:30** — fail-closed on
   `cannot create daemon attempt log: /home/ce-dev-2/ce-wall-daemon-...log`.
   `Restart=always` + StartLimit did their job; gate self-recovered at 05:30 after
   space was freed (~88G reclaimed), 3 clean passes verified (index 1–3, failed_count=0).
3. Transient du-vs-df gap (~89G) during the event = deleted-but-open files; resolved
   post-cleanup (du 211G ≈ df 212G). Note separately: the runsc seat holds 8×22G
   `memfd:runsc-memory` — that is RAM (known runsc-seat-in-RAM class), NOT disk;
   don't chase it as a disk consumer.

## B. Who eats the disk (measured 05:2x, before cleanup)

| Consumer | Size | Class |
|---|---|---|
| /home/ce-dev-1 (uncontained dev-1 controller) | **127G** | 44G .cache (per-ticket pytest basetemps: ce178 3.9G, ce294 1.5G, ce302 1.4G, ce298 1.4G, + 6.4G uv cache), 30G worktrees, 11G tmp, 8.7G two `*-pytest-live` dirs |
| /home/ce-dev-3 | 34G | seat-adjacent state |
| /var/tmp | 15G | 6.8G `pt-mq` + ~650M × N harvest worktrees (wt-h490, wt-h453a, wt-h518, wt-ce239…) — never reaped |
| /var/lib/containerd | 14G | incl. 7.0G orphan gVisor filestore snapshot 653 |
| docker images | 14.4G | 7.0G reclaimable (48%) |
| /swapfile | 8G | fine, leave |

**Root cause (class, not instance):** every workload writes unbounded scratch
(pytest basetemps, worktrees, caches) with NO age policy, NO quota, NO headroom
check, and NO reaper. Cleanups have been manual each time → recurrence is guaranteed.
dev-1 being uncontained makes it the largest unmetered writer.

## C. Fix design (implement in this order)

### F-1 — Host storage admission + reaping (elevate N-6 to FIRST landing)
1. **tmpfiles.d age policies** (host-level, root, one unit):
   `/var/tmp/wt-*` 48h · `/var/tmp/pt-*` 24h · `~ce-dev-1/.cache/*-pytest-tmp` 24h ·
   `~ce-dev-1/tmp` 72h · `~ce-dev-1/*-pytest-live` 24h.
2. **Headroom admission gate** (shared shell lib + validator check): full-parity/pytest
   suite refuses to START below 30G free; any ce daemon refuses to start below 5G with
   a distinct `disk_headroom` error (fail-closed BEFORE work, not mid-write).
3. **Reaper daemon** — deterministic, same promoted C5/gate template: sweep orphan
   worktrees + basetemps by age & absent lease, `docker image prune` (untagged only,
   keep pinned digests), containerd gVisor filestore GC for removed containers,
   `uv cache prune` weekly. Log reclaimed bytes per pass (auditable).
4. **Interim (today, one-time, controller-executed):** clear the measured consumers in
   §B rows 1/3/4/5 by the above age rules; keep anything under an active lease.

### F-2 — Gate hardening (small unit, big availability win)
1. Attempt-log path → systemd `LogsDirectory=` (or journald-only); the gate must never
   depend on a writable $HOME.
2. Startup disk-headroom check, distinct exit code (pairs with F-1.2).
3. **Liveness alarm:** gate already emits `daemon_pass_complete` every 120s — export
   last-pass timestamp to a state file; the N-2 acting-liveness watchdog pages when
   stale >3 intervals. (This outage was caught by a human supervisor session — that
   must never be the detection path.)

### F-3 — Controller-migration completeness runbook (the transition gaps, codified)
Convert the 2026-07-09 manual migration into a governed checklist unit; the four gaps
found in supervision become checklist items with acceptance evidence:
(a) `.claude/agents/` roles are NOT git-tracked → add to #931 snapshot manifest (or
commit them); (b) memory-dir sync + MEMORY.md; (c) creds provisioning matrix (what
travels never / what the Operator provisions); (d) session infra (crons/watchers)
recreate-list; (e) gate topology as declared IaC (N-8) incl. the UFW
`allow from 172.17.0.0/16 to any port 8200 proto tcp` rule that the gate needs to reach
local OpenBao (currently local-knowledge, undeclared).

### F-4 — Seat integrity closure
dev-4: RESTORED (verify ce-490 harvest completes from the wave). dev-3: repo venv
verified present at `/workspace/creator-engine/.venv/bin/python` — re-scope ce-ops#521
to per-worktree venv bootstrap or close with evidence.

### F-5 — dev-1 residue policy (until containment)
dev-1 is the largest unmetered disk writer (127G). Until the fleet-retirement program
contains it: its briefs must set named basetemps under a reaped root (F-1.1 covers),
and its controller prompt gains a standing "clean your per-ticket scratch at unit
close" obligation. Containment remains the real fix — do not let F-5 substitute.

## D. What is NOT broken (verified, avoid re-work)
- Gate: ACTIVE on VPS, migration-correct, singleton intact (DGX unit disabled).
- dev-4: container Up (2h); DGX disk 22% used — no DGX-side storage issue.
- dev-3 repo venv present; seat Working.
- Materializer: built + unarmed BY DESIGN — arming is an Operator decision that must
  return to the AWAITING-OPERATOR queue (it fell out during the crash checkpoints).
