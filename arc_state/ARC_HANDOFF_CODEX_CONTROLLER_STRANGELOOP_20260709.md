# ARC-DRIVING HANDOFF — ce-dev-2 SUCCESSOR CONTROLLER (codex harness) — 2026-07-09
# Author: ce-dev-2 Claude controller (post-migration, VPS). Audience: the ce-governed codex
# main controller launched in tmux session `ce-dev2-controller` on host ce-pilot-1.

## 0. OPERATOR RATIFICATION (verbatim authority, 2026-07-09 evening)
The Operator (asleep as of this handoff; will review in the morning) ratified:
- "launch a ce governed main codex controller attached to this tmux session (in the yolo mode
  of course) to take over when your claude max subscription hit limits" (weekly usage ~90%).
- "once you launch the ce governed codex controller make sure to hand him the full arc driving
  handoff so he continues to drive our current strangeLoop arc."
- "once you've launched the main ce governed codex controller make sure to hand him my
  ratification to drive the strangeLoop arc and give him all the information he needs."
YOU are that controller. You hold delegated authority to DRIVE the strangeLoop arc as the
ce-dev-2 persistent controller successor. One-face discipline: the Claude controller that wrote
this is winding down (usage cliff); it will not drive the arc concurrently. You are the face
once it halts. Do not relitigate ratified decisions (ce-operator-decides-relitigation).

## 1. WHO/WHERE YOU ARE
- Host: ce-pilot-1 (Hetzner VPS, x86_64). Unix user: ce-dev-2 (uid 1006). Sudo: NOPASSWD ALL.
  Docker group: yes (use `sudo -n docker ...` if your login session lacks the group).
- Repo: /home/ce-dev-2/creator-engine — origin/main @ 727f01a40a94f5ddcc43c52da4d0c2d31ce4718c.
  We run MAIN-HEAD internally (Option A ratified): ce installed editable from this checkout at
  /home/ce-dev-2/creator-engine/.venv/bin/ce (0.3.4+727f01a4). Keep it current: after main
  moves, `git fetch origin main && git merge --ff-only origin/main` (worktree is on main).
- Keys: ~/.ce-keys/ — overwatch.env (GH_TOKEN for reads/ops), ce-dev-2.pat (approvals),
  ce-root-v1{,.pass,.pub} (SIGNING — persistent-controller ONLY; workers/seats NEVER sign).
- Auth recipe: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`.
  Approve: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`.
  Merge queue: `gh pr merge <n> --auto --merge` (NEVER --squash). Approval IS the merge trigger
  (~120s). ISSUES live in ce-ops; CODE/PRs in creator-engine. Author≠reviewer always.
- Memory (REQUIRED reading, harness-agnostic): ~/.claude/projects/-home-ce-dev-2-creator-engine/
  memory/MEMORY.md is the identity index; topic files sit beside it. Read MEMORY.md NOW, then
  read a topic file BEFORE first use of its subject (index hooks can be stale).
- Emergency-migration context: .ce/BOOTSTRAP_README.md and
  .ce/state/research/RESUME_STATE_CE_DEV2_STRANGELOOP1F_EMERGENCY_20260709.md (the checkpoint
  this handoff extends). 481 salvaged local branches: .ce/local-branches.bundle.

## 2. BOARD AT HANDOFF (verified ~18:1x UTC 2026-07-09)
- 21 PRs merged today (#908–#929 minus #912). Merge queue EMPTY.
- Only open PR: #912 (ce-513 ratification-binding design) — OPERATOR-HELD design preview.
  Do NOT merge; design seats never self-declare green (ce-design-green-needs-operator-preview).
- Merge gate (ce-queue-daemon): ✅ MOVED TO THIS HOST 2026-07-09 (~18:15 UTC) — systemd unit
  `ce-queue-daemon.service` local on ce-pilot-1 (docker container ce-queue-daemon, drop-in
  10-vps-host.conf), DGX unit disabled to keep the singleton. Verified active. Cutover gotchas
  in memory topic ce-queue-daemon-systemd-dgx-deployment (uid-10001 chown, stale lease rm,
  reset-failed; redeploy via the ce-ops#895 script, NEVER nohup).

## 3. SEAT/FLEET STATE
- dev-3 (contained codex seat, container ce-vps-codex, THIS host, pane w1:p1): WORKING on
  ce-portability-guard-hygiene (S-class test hygiene; brief inside container at
  /var/tmp/BRIEF_portability_guard_hygiene.md, sha256 prefix a0001a3b9f95e0be). Expect signal
  `READY-FOR-HARVEST ce-portability-guard-hygiene <sha>` or `BLOCKED ...`. Seat venv is broken
  (ce-ops#521): if BLOCKED environmental-only, controller-side preflight is the attestation.
  Drive/read: `sudo -n docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock
  ce-vps-codex herdr pane read w1:p1 --source recent --lines 30` (send = `herdr agent send
  w1:p1 "<one-line pointer>"` then `herdr pane send-keys w1:p1 Enter`; if mid-turn use Tab).
  ⚠️ `Implement {feature}` in the composer is codex's IDLE PLACEHOLDER, not a stuck dispatch —
  judge by the `Working (Xs)` spinner / scrollback growth (ce-herdr-dispatch-landing-misread).
- dev-1 (user ce-dev-1, tmux ce-dev1-orchestrator): SEPARATE PEER CONTROLLER (codex). Do not
  drive it; coordinate peer-to-peer. It holds unpushed branch ce-496 rescue @6f85f4de (§5).
- dev-4 (contained seat ce-dgx-codex) + merge gate: ON THE DGX — currently UNREACHABLE (§4).
- Arad/Mythos: first live tenant, on 0.3.4; Arad-install codex controller lives on the DGX
  (idle/complete). Tenant defects → tenant-class ce-ops tickets.

## 4. ⚠️ BLOCKING GAP — VPS→DGX SSH (report status to Operator in the morning)
The DGX (dgx-spark-1, 100.100.105.50) is tailnet-active with port 22 open, but NO key on this
host authenticates (ce-dev-2 has no ssh private key; legacy /home/ce/.ssh/id_ed25519 is
rejected). Historically access was DGX→VPS only. CONSEQUENCES (narrowed now the gate is local,
§2): cannot restore dev-4, cannot reach the DGX salvage transcripts, cannot reach the
Arad-install controller tmux. AWAITING-OPERATOR: provision a VPS→DGX ssh credential (or run
`tailscale ssh`/authorize a key from the DGX side). Until then, treat every DGX-dependent item
as BLOCKED — do not burn cycles.

## 5. THE FOUR DEAD WORKER MANDATES (from STRANGELOOP1F; status after my partial recovery)
1. Harvest ce-497 (controller-state-sync-s1) @4871b8990adcb511857fef1bf1d57981725c830e and
   ce-506 (daemon-vs-agent-rubric-design-s1) @b845d9f060117ebc3f8609c3c8cf77fe956ed361:
   ✅ BOTH branches already extracted from dev-3 and sit in the LOCAL repo (verified additions-
   only, changelog+carrier present, 1 commit behind main). REMAINING: run FULL `ce validate-pr`
   preflight per branch (host preflight = sole attestation, dev-3 venv broken), push, open PRs
   (carrier slug MUST equal branch slug; PR body needs `- **Declared work class:** <class>`),
   review via governed reviewer, approve as ce-dev-2, `gh pr merge --auto --merge`.
   ce-506 caveat: docs/design boundary lens; it is a DESIGN doc — check whether it needs the
   Operator-preview hold like #912 before merging (default: hold design docs for Operator).
2. Harvest ce-490 (contained-launch-preflight-s1, manifest .ce/pr-manifests/
   ce-490-contained-launch-preflight-s1.md): BLOCKED on dev-4/DGX (§4). Park until ssh restored.
3. ce-496 rescue: branch parked UNPUSHED on dev-1 @6f85f4de. Dispatch to dev-1 (peer request,
   not an order): scrub confidentiality literals, NEVER weaken tests, gap-honesty lens.
4. ce-516 Item-3 (brain-window): workflow fail-open comment fix + record-65 fresh precompute
   (byte-change rule). HOLDS THE EXCLUSIVE brain-ledger window. Re-dispatch to a governed
   worker (dev-3 next free, or a local implementer worktree). The serialized brain-window queue
   AFTER it: ce-478 pyproject pin → ce-453 Part A → #500 slices a/d. NEVER run two brain-ledger
   writers concurrently.

## 6. STANDING MANDATES (priority order, unchanged)
1. MAIN-CONTROLLER INDEPENDENCE (the migration that just happened IS this mandate).
2. NO IDLE SEATS — 159-ticket backlog; idle seat + stocked backlog = controller failure.
   Restock queues BEFORE they drain (ce-multi-ticket-batch-dispatch).
3. Worker routing: hardest work → dev-4 (when back); Haiku-tier = verify-only;
   never Sonnet 5 for subagents; omit model on pinned roles.
4. Gate discipline: FULL validate-pr GREEN before push; per-PR changelog; carrier required;
   G5 work-class line in PR body; bounded work-units; release cut off CURRENT main.
5. Context hygiene: at >45% context used, checkpoint to .ce/state/research/ and /clear
   (write RESUME_STATE_CE_DEV2_<marker>.md, newest-by-mtime is authoritative; NEVER .hermes).
6. AWAITING-OPERATOR queue (absolute paths, forge-visible): PR #912 (held), arc report
   /home/ce-dev-2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md
   (UNWRITTEN — write it), Nitzan D6, STRANGELOOP-2 mandate draft (fold in: two DGX incidents
   2026-07-09, controller→VPS migration, /tmp-toml footgun recurrence, the `Implement {feature}`
   placeholder MISDIAGNOSIS — it was codex idle UI, not a composer bug — and dev-3 venv gap
   ce-ops#521), PLUS new: VPS→DGX ssh credential gap (§4).

## 7. SESSION INFRA YOU MUST (RE)CREATE — died with the DGX session
NOTE: the outgoing Claude controller armed a PASSIVE bridging watcher only (logs dev-3
READY/BLOCKED signals to .ce/state/fleet-signals.log, acts on nothing). Replace it with your
own ACTING infra below, then `pkill -f fleet-signal-bridge` to retire the bridge.
1. Dev-check cron `21,51 * * * *`: full board pass — gate/PR watch, seat probes, restock.
   ACT, don't just report.
2. Fleet signal watcher: probe reachable seats for READY-FOR-HARVEST/BLOCKED lines every 180s,
   dedup repeats. (Only dev-3 probe-able until §4 resolves.)
3. Arm a watcher for EVERY dispatch (ce-arm-watcher-for-every-dispatch): pair each seat
   dispatch with a stall watcher.

## 8. YOUR OWN LIFECYCLE
- You were launched via `ce launch` with a `ce takeover --dry-run --json` evidence packet
  (governed continuity path, ce-ops#471 P0). Your CODEX_HOME is ~/.codex (fleet account
  neckar@, acct 2dc1bc68 — shared weekly pool; don't self-throttle, but don't waste).
- The Claude controller may still be alive finishing memory updates + its wind-down report.
  It will NOT drive the arc after this handoff lands. If you see its tmux window, leave it.
- Checkpoint discipline applies to you too (§6.5). Your first checkpoint marker: STRANGELOOP1G.
- When the Operator wakes: greet with the §4 gap, the board delta, and AWAITING-OPERATOR list.

## 9. FIRST ACTS (suggested order)
1. Read MEMORY.md + this file end-to-end. `source` the auth recipe. Verify `gh api user` =
   ce-overwatch and `git -C ~/creator-engine rev-parse origin/main` = 727f01a4...
2. Recreate §7 infra (cron + watcher).
3. Preflight + push + PR the two extracted harvest branches (§5.1) — closest to merge, and it
   proves your full gate loop end-to-end.
4. Re-dispatch ce-516 Item-3 (§5.4) — it holds the brain window; the queue behind it is idle
   until it lands.
5. Peer-request the ce-496 rescue push from dev-1 (§5.3).
6. Watch dev-3 for its READY/BLOCKED signal and harvest per ce-harvest discipline.
7. Write the arc report (§6.6) between waits.
