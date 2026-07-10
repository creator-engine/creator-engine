# RESUME STATE — CE-DEV-2 Controller · Day-shift arc · 2026-06-26T12:00Z (CHECKPOINT — two operating-model changes; read carefully)

## ⚠️ SEAT IDENTITY & TOPOLOGY — READ FIRST (full detail: MEMORY.md READ-FIRST block)
DGX Spark, cedev2 uid1003, `~/creator-engine`. Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`. Fleet on neckar@. Creds: overwatch `~/.ce-keys/overwatch.env`→`GH_TOKEN=$CE_OVERWATCH_PAT`; reviewer `~/.ce-keys/ce-dev-2.pat`.
- dev-1 = NON-contained codex, tmux `ce-dev1-orchestrator`, `/home/ce-dev-1/creator-engine`, `ssh dev1`. Reviews as **ce-dev-1**.
- dev-3 = CONTAINED `ce-vps-codex` (VPS), `ssh dev1 'sudo docker exec -u ce-dev-3 ce-vps-codex bash -lc "…"'`.
- dev-4 = CONTAINED `ce-dgx-codex` (LOCAL), `sudo docker exec ce-dgx-codex bash -lc "…"`.
- **Dispatch (reliable):** write packet to seat's `tmp/`, then **base64-DECODE-the-message-ON-REMOTE** → herdr `pane send-text w1:p1 "$M"` + `send-keys w1:p1 Enter` (SOCK=/run/creator-engine/herdr/herdr.sock); dev-1 via `tmux send-keys -l`. Raw `<>`/`#`/parens MANGLE. Stuck-menu → `send-keys Escape`.

## 🔁 OPERATING MODEL — TWO CHANGES THIS SESSION (do NOT revert)
**(1) Merge mechanics OFF the frontier model** ([[ce-merge-mechanics-off-frontier-model]]): harvest/enqueue/update-branch/queue-watch → general-purpose workers `model: sonnet` (validated — sonnet harvests + a sonnet `reviewer`-role review of #515 both worked great); enqueue of APPROVED+green+CLEAN → the `:30` cron `ce-conveyor-tend.sh` stranded-sweep (modelless). Routine review → cheap governed `reviewer` role on sonnet (controller submits as ce-dev-2). Opus reserved for genuine/security/architecture review + Operator interface. NO ambient-cred tender (charter parked `.ce/state/parked/CONVEYOR_TENDER_CHARTER.parked.md`).

**(2) MULTI-TICKET BATCH dispatch** ([[ce-multi-ticket-batch-dispatch]]): a codex seat is NOT single-ticketed — it runs SEVERAL file-DISJOINT tickets concurrently via codex worktrees + background subagent-threads. Controller's job = partition safe (non-overlapping) batches; the seat spawns a background subagent-thread in its own git worktree per ticket. Codex CLI mechanics: explicit spawn ("Create a separate background thread in a worktree to do X"), `/agent` (inspect/switch), `/new`, `/ps`, `/stop`, roles in `config.toml [agents]`. Packet form = born-a-foreman + N embedded tickets + `git worktree add` per ticket + "if two need a shared file, serialize." **Disjointness must be checked vs OTHER seats AND vs IN-FLIGHT open PRs** (lived: #177 collided with un-merged #515 in the brain subsystem). **PROBE current main before dispatching** — an OPEN ticket may already be resolved by a merged PR (lived: #239 was already done by #446; wasted a dev-4 cycle).

## 🎯 EGRESS CHAIN — link 1+2 DONE, #242 is the prize (top next-dispatch)
The contained controller/tender can't push until a contained seat gets a credentialed egress. Status (CORRECTED this session):
1. ✅ **#514/#240** fail-closed `gh` credential SEAM — MERGED.
2. ✅ **#239** OpenBao/SecretIdentityBackend SUPPLIER — ALREADY DONE via merged **#446** (v3_cli `_approval_wall_runtime_from_args` threads `approval_wall_secret_supplier_from_secret_identity_backend`, tested). ce-ops#239 + redundant PR #518 CLOSED.
3. 🔓 **#242** (contained-seat SELF-PUSH via injected cred) — **UNBLOCKED, top next-dispatch.** dev-4 is the natural owner (built the seam). + **#243** (self-review) also unblocked.
→ Then a CONTAINED, per-call-cred-injected, MODELLESS Integrator (#216) runs the conveyor — retires even the sonnet mechanics spend. THAT is the endgame.

## FLEET (all Working on multi-ticket batches)
- dev-1 → BATCH: **finish-#177** (rebase ce177 onto main+#515, resolve additive brain conflict) + **#251** (work-class doc) + **#260** (release-artifact parity guard). Packet `tmp/PKT_dev1_batch.md`.
- dev-3 → **#237** (herdr authenticated reach plane) — single; batch it next stop-line.
- dev-4 → BATCH: **#256** (retire host-tmux→detached+systemd) + **#226** (cockpit peek; ⚠️ watch #226↔#237 herdr overlap). Packet `tmp/PKT_dev4_batch.md`.

## CONVEYOR (main 8fe46da) — nearly clear
- ⚠️ **#507** (#244 Worker tier): APPROVED+auto, long-BLOCKED — WATCH; check why it hasn't drained (re-run? a non-currency failure?). Possibly the last currency straggler or a real check — diagnose.
- Merged this session: #504/#505/#506/#508/#509/#510/#511/#512/#513/#514/#515/#516/#517/#498.

## TICKETS FILED / CLOSED THIS SESSION
- Filed: #259 (ce worker run — LANDED as #517), #260 (release-hash guard — dev-1 building). 
- Closed: #239 + #518 (already done via #446).
- Install/release audit (→ #260): site↔README↔code byte-identical; only signature = SSHSIG on llms-install.md; "signed playbook" = the agent-native signed install spec (NOT `ce playbook run`). D1 (policy-doc v0.1.0-vs-shipped-0.2.0) + D3 (wording) → public-docs pass.

## NEXT ACTIONS
1. **#242 (contained self-push)** → dispatch to dev-4 when its batch clears (egress endgame). Then #243.
2. Diagnose + drain **#507**.
3. Harvest batch outputs (dev-1 #177/#251/#260, dev-4 #256/#226, dev-3 #237) on SONNET → review (routine→sonnet reviewer, genuine→Opus) → enqueue. Retask each freed seat with a NEW disjoint BATCH (probe-not-already-done + check-vs-in-flight-PRs).
4. Hold Opus to partition + genuine review + Operator interface. Mechanics → cron/sonnet. NO ambient-cred shortcuts.
5. Surface to Operator ONLY: autonomy canary, reserved R1-R6, auto-halt.

## STANDING AUTHORITY: G1-G5 granted, R1-R6 reserved. Operator driving turn-by-turn (no autonomous /loop armed).
