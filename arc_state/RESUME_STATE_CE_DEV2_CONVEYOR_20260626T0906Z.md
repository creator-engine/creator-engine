# RESUME STATE — CE-DEV-2 Controller · Day-shift arc · 2026-06-26T09:06Z (CHECKPOINT for fresh context)

## ⚠️ SEAT IDENTITY & TOPOLOGY — READ FIRST
THIS host = **DGX Spark** (`spark-b824`, user `cedev2` uid1003, GB10 aarch64). Controller CE-DEV-2 runs ON the DGX, `~/creator-engine`. Foreman model: ALL substantive work → launched seats; controller holds coordination + merge gate.
- **dev-1** = NON-contained codex in tmux `ce-dev1-orchestrator` (%0) on Hetzner VPS (user ce-dev-1, `~/creator-engine`). Reach: `ssh dev1`.
- **dev-3** = CONTAINED container `ce-vps-codex` on VPS (`/workspace/creator-engine`). Reach: `ssh dev1 'sudo docker exec -u ce-dev-3 ce-vps-codex bash -lc "..."'`; herdr socket `/run/creator-engine/herdr/herdr.sock` pane `w1:p1`.
- **dev-4** = CONTAINED container `ce-dgx-codex` LOCAL on DGX. Reach: `sudo docker exec ce-dgx-codex bash -lc "..."`. Real codex home = host **`/home/cedev4/.codex-contained`** (NOT .codex). Relaunch AS cedev4 (`ssh cedev4@localhost`, uid1002, docker group).
- Creds: overwatch (`~/.ce-keys/overwatch.env` → `GH_TOKEN=$CE_OVERWATCH_PAT`, author/push/merge) ; reviewer (`~/.ce-keys/ce-dev-2.pat`, ce-dev-2 identity). ISSUES=ce-ops repo; CODE/PRs=creator-engine.
- Resume on fresh context: read MEMORY.md + newest `RESUME_STATE_CE_DEV2_*` (this file). Drive = autonomous /loop (see bottom).

## ACCOUNTS — verify by EMAIL ([[ce-openai-account-email-mapping]])
Fleet on **neckar@gmail.com** (Operator reset its 5h pool). Other sub = **amitaicoco1@** (token backed up per seat as auth.json.bak.*). NEVER trust A/B labels or .bak filenames — decode auth.json id_token email claim. A seat showing "usage limit" is usually the WRONG account or stale transcript (confirm via • Working indicator; nudge frozen seats "continue").

## FLEET (all Working on neckar@, all foremen) @ 09:06Z
- dev-1: **ce-ops#166 slice-2** (branch `ce166-knowledge-ssot-slice2`) — write-once fleet propagation + bounded assertion migration.
- dev-3: **ce-ops#248** (branch `ce248-playbook-run-exec`) — `ce playbook run` executor.
- dev-4: **ce-ops#235** (branch `ce235-dequeue-settle`) — DEQUEUE primitive + integrator settle window.

## CONVEYOR / MERGE TRAIN (main HEAD daeffd34)
- ✅ MERGED today: #489-497 batch + #499(#163) #500(#256 detached) #501(#249 guard) #502(#20 spine) #503(#166-s1) #496(#241 parity) + ce-ops#257(runbook).
- 🔵 IN QUEUE/draining (APPROVED, --auto, BLOCKED=CI running, will merge — NO manual update-branch needed): **#505**(#252 validate-pr), **#504**(#250 test-hardening).
- ⏳ HARVEST WORKERS RUNNING (will open PRs ~#506/#507): dev-1 #244 (Worker tier, branch ce244-worker-tier @ 6e4d215) + dev-4 #253 (controller inbox, branch ce253-controller-inbox @ 7ba40c3). When they report: review-as-ce-dev-2 (cross-model) + enqueue.
- ⏸️ HELD: **#498**(#198 fix) DIRTY + controller-authored → needs PEER review (NO controller self-approval — interim discipline until contained controller).

## ⭐ KEY DECISIONS/LEARNINGS TODAY (all banked to memory)
1. **strict OFF** — "require branches up-to-date" + merge queue = O(N²) rebase-loop-hell. Disabled in BOTH ruleset (ce-reference-protection-floor) + classic protection. Safety unchanged (queue tests merge-group). Going forward: just enqueue approved+green (BEHIND ok); update-branch ONLY for DIRTY conflicts. [[ce-merge-queue-strict-antipattern]]
2. **ADR grading model RATIFIED** (spine-first; mode=delegation-level; cross-model independence; autonomous live-merge HELD behind contained controller). [[ce-grading-model-mode-parameterized]] Live-executor + wall-guard HELD (ADR D9.3).
3. **Merge queue GROUPS PRs (ALLGREEN, max 5)** — one bad PR fails the whole group + evicts (#496 dangling-links poisoned batches until fixed). #501 added the dangling-link guard. Fix offender, don't fight queue.
4. **Stranded-PR sweep** folded into conveyor-tend (:30) — ce-ops#258; guards: skip already-queued + skip recent-merge_group-failed (avoid loop). Queue membership via mergeQueue.entries GraphQL, NOT autoMergeRequest (null for queue entries).
5. **#250 already fixed by #256** (launcher auto-clears session.json→prelaunch-backup); use CURRENT main launcher.
6. **Forks: one mandate then die** [[ce-fork-lifecycle-one-mandate-then-die]].

## STANDING AUTHORITY (DAYSHIFT_ARC_20260626_AUTHORITY_MANIFEST.md)
G1-G5 GRANTED (conveyor merge / queue+dispatch+seat-lifecycle / #249 / OpenBao wall routine / autonomy canary). R1-R6 RESERVED (fleet-wide rollout / external release-Arad / git-history-scrub / grant-beyond-envelope-or-weaken-guard / irreversible-outside-set / new high-consequence scope). Auto-halt → Operator.

## FOLLOW-UPS (parked, not urgent)
- `CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md` reads internal-ops → candidate ce-ops relocation under #249.
- Runbook #257's manual session.json-clear step now redundant (launcher auto-clears) — minor doc note.
- ce-ops open units remaining (non-autonomy): #236/#237/#238 (Dev Mode contained-controller legs), #226 (cockpit peek), #251 (work-class doc), #233/#231. Autonomy #242/#243 HELD behind contained controller.

## NEXT ACTIONS (autonomous /loop continues)
1. When harvest workers report (#244/#253 PRs): cross-model review + enqueue.
2. Confirm #504/#505 merge (queue auto-drains post-strict-off).
3. Seats hit stop-lines → harvest + retask next arc units (born-a-foreman packet; pick from open ce-ops). Contained relaunch recipe = clear herdr session.json + CODEX_HOME=.codex-contained (dev-4) + resume by EXPLICIT session id (not --last).
4. Surface to Operator ONLY: autonomy canary report, reserved R1-R6, auto-halt.
