# RESUME STATE — CE-DEV-2 Controller · Day-shift arc · 2026-06-26T10:30Z (CHECKPOINT for fresh context)

## ⚠️ SEAT IDENTITY & TOPOLOGY — READ FIRST (full detail: MEMORY.md READ-FIRST block)
THIS host = **DGX Spark** (`cedev2` uid1003, `~/creator-engine`). Controller=foreman: substantive work → seats; controller holds coordination + merge gate. Repo slug = **creator-engine/creator-engine**; ISSUES = **creator-engine/ce-ops**.
- **dev-1** = NON-contained codex, tmux `ce-dev1-orchestrator` on VPS, repo `/home/ce-dev-1/creator-engine`. Reach `ssh dev1`. Reviews as **ce-dev-1** (own GH identity = valid peer). Dispatch: write packet to its `~/creator-engine/tmp/`, then **base64-on-remote** send (`M=$(echo <b64>|base64 -d); tmux send-keys -t ce-dev1-orchestrator -l "$M"; tmux send-keys ... Enter`) — plain send mangles on `#`/`<>`/parens.
- **dev-3** = CONTAINED `ce-vps-codex` on VPS. Reach `ssh dev1 'sudo docker exec -u ce-dev-3 ce-vps-codex bash -lc "…"'`. Dispatch: packet to `/workspace/creator-engine/tmp/`, herdr `HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr pane send-text w1:p1 "$M"` + `send-keys w1:p1 Enter` (base64-decode the msg on-remote; avoid `<>`). Verify via `herdr pane read w1:p1 --source recent` (look for `Working`).
- **dev-4** = CONTAINED `ce-dgx-codex` LOCAL on DGX. Reach `sudo docker exec ce-dgx-codex bash -lc "…"` (no ssh). Same herdr dispatch. If TUI stuck in a menu: `herdr pane send-keys w1:p1 Escape` first.
- Creds: overwatch `~/.ce-keys/overwatch.env`→`GH_TOKEN=$CE_OVERWATCH_PAT`; reviewer `~/.ce-keys/ce-dev-2.pat`. Fleet on **neckar@**.

## FLEET (all foremen; retasked 10:25Z) — they DRIVE via own sub-threads, no controller inlining
- **dev-1**: ce-ops#166 slice-2 **brain-ledger re-pin** (re-pin `validate.yml` evidence sha256 to `598735ee…` + re-chain hash records 3→5; #510 changed validate.yml → drift). Packet `tmp/PKT_dev1_ce166_repin.md`. **Then** #498 re-review queued.
- **dev-3**: ce-ops#233 harden verify-by-reaction dispatch confirmation (branch `ce233-harden-verify-by-reaction`). Packet `tmp/PKT_dev3_ce233.md`.
- **dev-4**: ce-ops#259 `ce worker run --role` governed launch-and-collect (branch `ce259-worker-run`). Packet `tmp/PKT_dev4_ce259.md`. ⚠️ **dev-4 at ~11% context** — relying on foreman sub-thread delegation; if its #259 PR is weak, re-dispatch on a fresh/relaunched seat.

## CONVEYOR / MERGE TRAIN (main HEAD 21c0f84)
- ✅ MERGED this session: #505(#252 validate-pr), #508(#248 playbook), #504(#250 herdr flaky), #506(#253 inbox), #510(CI live-base churn-fix), #509(#252 CI-parity), #511(#235 dequeue), #512(#188 claim-bridge).
- 🔵 **#513**(#224 lane row, dev-3): APPROVED+auto → draining. **#507**(#244 Worker tier): APPROVED+auto, finally has #510's tolerant workflow (after final update-branch) → draining.
- 🟡 **#498**(#198 dogfood, dev-4-authored): rebased onto 21c0f84 → head **14458fb** (force-pushed; was DIRTY, now BLOCKED/mergeable), carrier ok, NEW=0, confidentiality fix re-applied. **Re-review QUEUED to dev-1** (only conflict-res + conf-fix changed vs prior approval). Enqueue once dev-1 re-approves.
- ⏳ **dev-4 #240 harvest worker still running** → PR incoming (contained-controller scaffold + fail-closed credential seam). When it reports: cross-model review + enqueue.

## ⭐ KEY LEARNINGS / DECISIONS THIS SESSION
1. **`ce validate-pr` shipped unit-only (narrower than CI)** → false-green let #507's integration failure through harvest. Fixed by #509 (default = full tree). [[ce-run-full-preflight-before-push]]. **Harvest baseline-diff MUST run the FULL suite** (`validators/tests/ -m "not wheel_bake_gate" -n auto --dist loadgroup`).
2. **Live-comparison base-currency check resurrected rebase-churn** even with strict-off (it hard-failed behind-PRs in pull_request context). Fixed by #510 (scope to merge_group). In-flight PRs branched pre-#510 need ONE update-branch to adopt the tolerant workflow, then no more churn.
3. **CE worker-launch GAP** (→ ce-ops#259): controller could not cleanly launch a governed worker by role (`ce lane launch` on v1 `ce` vs `cev3 dispatch --spawn`; role-def in `.claude/agents/` divorced from launch; declared tools ≠ lane runtime egress; no findings round-trip) → **bypassed to ungoverned harness agent**. dev-4 building the fix. Controller-facing half of contained-controller arc (#236/#240).
4. **Install/release audit** (→ ce-ops#260): site↔README↔code are byte-identical (sha256-proven, in sync). Only signature = SSHSIG on `llms-install.md`; "signed playbook" = the agent-native signed install spec (NOT `ce playbook run`, which is unsigned). Merging publishes NOTHING — release is a MANUAL Operator-gated cut. Drifts: **D4** served `install.sh` hash ≠ published SHA256SUMS (stale mirror, inside signed surface) → #260 + CI guard; **D1** policy doc says v0.1.0 vs shipped 0.2.0; **D3** "signed playbook" wording.
5. **Shared-worktree race** — fork worktrees can get hijacked (the #498 rebase worktree got another agent's checkout); commits safe in the ref; push by explicit SHA from a fresh checkout. [[ce-fork-shared-worktree-race]]
6. **Contained-seat dispatch:** base64-decode the message on-remote; `<>`/`#`/parens in a raw send-text mangle the shell command.

## STANDING AUTHORITY (DAYSHIFT_ARC_20260626 manifest)
G1-G5 GRANTED (conveyor merge / queue+dispatch+seat-lifecycle / #249 / OpenBao wall / autonomy canary). R1-R6 RESERVED. Operator driving turn-by-turn (autonomous /loop NOT armed).

## NEXT ACTIONS
1. dev-4 #240 harvest reports → cross-model review + enqueue (flag if it touches `.github/workflows`).
2. dev-1 finishes #166 re-pin → re-harvest #166 slice-2 (was blocked on the validate.yml hash drift); then dev-1 does #498 re-review → enqueue #498.
3. Watch #513 + #507 drain.
4. Seats hit stop-lines → harvest (FULL-suite baseline) + retask. Open ce-ops: #234/#237/#238/#239/#251/#226/#177/#260.
5. dev-4 #259 + dev-3 #233 → harvest + review when they report.
6. Surface to Operator ONLY: autonomy canary, reserved R1-R6, auto-halt.
