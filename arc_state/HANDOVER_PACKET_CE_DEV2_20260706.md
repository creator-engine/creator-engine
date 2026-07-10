# CE-DEV-2 CONTROLLER HANDOVER PACKET — 2026-07-06 (living doc; controller updates before each quota cliff)
Purpose: governed codex controller takes over CE-DEV-2 duties when the Claude controller hits limits; hands back on reset. This is ALSO the live test-drive of the ce-takeover continuity design (ce-ops#471) — log every friction point you hit into a TAKEOVER_FRICTION log section at the bottom; that's research evidence.

## LAUNCH (Operator or outgoing controller runs)
1. Preconditions (already applied 2026-07-06): ~/.codex/config.toml has `approval_policy = "never"` + `sandbox_mode = "danger-full-access"` (CDX-D-6 config mode); ~/.codex/app-server-daemon/settings.json remoteControlEnabled=false (CDX-D-2). Backup at ~/.codex/config.toml.bak-20260706-pretakeover.
2. Launch: `cd ~/creator-engine && .venv/bin/ce launch --harness codex` → tmux session `ce-controller`, window `controller`, operator-visible. Dry-run verified GREEN 2026-07-06 ~08:4xZ.
3. First message to the pane: "You are CE-DEV-2 (interim governed codex controller). Read /home/cedev2/creator-engine/.ce/state/research/HANDOVER_PACKET_CE_DEV2_20260706.md fully, verify its sha256 against the value the Operator gives you, then execute its STARTUP section."

## STARTUP (incoming controller)
1. Read IN FULL, in order: (a) /home/cedev2/.claude/projects/-home-cedev2-creator-engine/memory/MEMORY.md — the knowledge index; treat every hook as a pointer, READ the topic file (same dir) before first use of any policy; (b) newest .ce/state/research/RESUME_STATE_CE_DEV2_* by mtime; (c) .ce/state/research/DAYARC_MANDATE_CE_DEV2_20260706.md (ratified, incl. 0.3.3 addendum); (d) playbooks/controller/briefs/{dispatch,harvest,merge-gate}.md.
2. Surface ⏸️ AWAITING-OPERATOR items FIRST (queue rule).
3. Re-arm watchers: PR-board poll loop (90s, `gh pr list --state all --limit 15` diff); Nitzan D6 follow-up if still unanswered.
4. Check in-flight work: .ce/claims/ = live claims; `git worktree list` under .ce/wt-*; background Claude subagents DIED with the outgoing session — check their worktrees for partial state before re-dispatching (verify, never assume).

## AUTHORITY & CAPABILITIES (parity grant)
- Auth: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT` (push/PR/read). Approve: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve` — approval IS the merge trigger (wall daemon merges ~120s; daemon health: pid via `pgrep -f queue-daemon`, log at the rollback-relaunch.log path in the newest resume state).
- Dispatch/harvest exactly per playbooks: brief-to-file + sha256 pointer, territory check, claims recorded; seats: dev-1 ssh dev1 tmux ce-dev1-orchestrator:2.0; dev-3 via ssh dev1 + docker exec ce-vps-codex + herdr (socket INSIDE container at /run/creator-engine/herdr/herdr.sock); dev-4 via sudo docker exec ce-dgx-codex + herdr (same in-container socket path). runsc docker cp broken → bundle + exec-cat.
- Reviews: dispatch review-ANALYSIS to codex seats (token policy 2026-07-06: divert everything codex-doable to codex); the APPROVAL submission is always ce-dev-2 PAT, author≠approver holds.
- Full `ce validate-pr` GREEN one pass before any push; carrier via write_carriers; changelog fragment; `- **Declared work class:** tiny|story|feature|epic` in PR body.

## ⛔ HARD STOP LINES (non-negotiable for the interim controller)
1. **NO ce-root-v1 SIGNING.** Non-delegable. If the 0.3.3 release reaches sign-ready: STOP, notify the Operator — Operator either signs manually per .ce/release-staging/0.3.2/SIGNING-INSTRUCTIONS.md (adapted to 0.3.3) or parks until the Claude controller returns. Never touch ~/.ce-keys/ce-root-v1.
2. No repo-settings/branch-protection mutation; no arming dep-unlock (D4 = Operator, post-soak); no external comms (Arad send = Operator); R-class → halt → Operator.
3. No new memory-file edits in the Claude memory dir except appending to THIS file's friction log and writing RESUME_STATE_* checkpoints (harness-neutral, .ce/state/research/).
4. Session hygiene: checkpoint state to a new RESUME_STATE_CE_DEV2_* before any /clear-equivalent; dual-write habit stands.

## STATE SNAPSHOT (as of ~08:4xZ 2026-07-06 — verify against live board, do not trust blindly)
- Merged today: #847 #848 #849 #850 #851 #852 #853 #854 #855; #856 approved/CLEAN (likely merged by the time you read this).
- CRITICAL PATH: 0.3.3 minimal release (ratified addendum in the mandate): builder worktree .ce/wt-ce-release-0.3.3 (Claude subagent may have died mid-build — inspect; if incomplete, re-dispatch the build to dev-4 with the same brief shape: version bump, wheel, downloads+staging mirror of 0.3.2 layout, SHA256SUMS, spec canonical bytes, STOP at signature per stop-line 1). After merge+tag: #851's chain auto-publishes images; then digest-pin PR; then canary C rerun (see /var/tmp/ce-canary-c2/CANARY_C2_LOG.md — installation_id 141552951 acct-wide; PEM staging per custody rule is CONTROLLER-INLINE... for interim controller: STOP at the PEM step too, Operator handles, key custody is not yours); then Arad pack completion → Operator sends (D2).
- Seats: dev-3 building #461 (commit-only → harvest); dev-1 idle → restock (#464 sweep design or next backlog); dev-4 idle → restock (reviews + builds; strongest seat).
- Research in flight: controller-power report (ce-ops#471) via a Claude subagent — if it died, its brief is .ce/briefs/BRIEF_research_controller_power_continuity_20260706.md; re-dispatch to dev-4.
- Pending Operator: D6 Nitzan 7 answers; 0.3.3 signing when sign-ready; Arad send; #471 report assessment.

## HANDBACK (when Claude limits reset)
Write RESUME_STATE_CE_DEV2_HANDBACK_<ts>.md (what you did, board state, in-flight, friction log pointer); Operator relaunches Claude controller; it reads MEMORY.md → newest resume state → this packet's friction log.

## TAKEOVER_FRICTION LOG (append-only, evidence for ce-ops#471)
- 2026-07-06 pre-takeover: CDX-D-6 refused argv bypass (fixed via config keys); CDX-D-2 remote-control was enabled (disabled); --no-tmux refused (G6-LAUNCH-HIDDEN) — all three correct-but-undocumented-at-point-of-need; a takeover verb would have handled all three.
- 2026-07-06 codex standby hydration: `git ls-remote` emitted a credential-helper traceback (`mint-forge-token.py` missing `jwt`) before still returning some refs; watcher re-arm by ad hoc shell loop was brittle (self-matched pgrep guard, then one-shot exit). A takeover verb should provide durable named watchers + health checks instead of shell quoting.

## ADDITION 2026-07-06 ~19:0xZ (Operator directive: controller-agnostic memory)
After the resume state, ALSO read .ce/state/decisions/ (newest file first) — Operator decisions live there, controller-agnostically. The Claude controller MEMORY.md index is Claude-private and NOT your dependency.
