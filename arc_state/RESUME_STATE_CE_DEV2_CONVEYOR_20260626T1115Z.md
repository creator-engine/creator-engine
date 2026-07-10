# RESUME STATE — CE-DEV-2 Controller · Day-shift arc · 2026-06-26T11:15Z (CHECKPOINT — operating model CHANGED, read carefully)

## ⚠️ SEAT IDENTITY & TOPOLOGY — READ FIRST (full detail: MEMORY.md READ-FIRST block)
THIS host = DGX Spark (cedev2 uid1003, `~/creator-engine`). Repo slug `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`. Fleet on neckar@. Creds: overwatch `~/.ce-keys/overwatch.env`→`GH_TOKEN=$CE_OVERWATCH_PAT`; reviewer `~/.ce-keys/ce-dev-2.pat`.
- dev-1 = NON-contained codex, tmux `ce-dev1-orchestrator`, host repo `/home/ce-dev-1/creator-engine`, `ssh dev1`. Reviews as **ce-dev-1**.
- dev-3 = CONTAINED `ce-vps-codex` (VPS), `ssh dev1 'sudo docker exec -u ce-dev-3 ce-vps-codex bash -lc "…"'`.
- dev-4 = CONTAINED `ce-dgx-codex` (LOCAL), `sudo docker exec ce-dgx-codex bash -lc "…"`.
- **Seat dispatch (contained):** write packet to seat's `/workspace/creator-engine/tmp/`, then **base64-DECODE-the-message-ON-REMOTE** → `herdr pane send-text w1:p1 "$M"` + `send-keys w1:p1 Enter` (HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock). Raw `<>`/`#`/parens in send-text MANGLE. If TUI stuck in a menu: `send-keys w1:p1 Escape` first. dev-1 (tmux): same base64-on-remote via `tmux send-keys`.

## 🔁 OPERATING MODEL — CHANGED THIS SESSION (do NOT revert)
**Operator directive: stop burning Opus on merge mechanics.** Chosen model = **B**:
- **Mechanics (harvest extract→rebase→full-suite-baseline→carrier→push→PR; enqueue; update-branch; queue-watch) → NOT Opus.** Harvests → dispatch general-purpose workers with `model: sonnet`. Enqueue of APPROVED+green+CLEAN PRs → the deterministic `:30` cron `ce-conveyor-tend.sh` stranded-sweep (modelless) — let it run; nudge `gh pr merge <n> --auto` only if impatient.
- **Routine review → cheap governed `reviewer` role on `model: sonnet`** (it returns a verdict; controller submits as ce-dev-2). Worked great this session (thorough hash-chain review of #515 on sonnet). The CE governed agent types (`architect_research`/`implementer`/`reviewer`/`verification`) are now available as Agent subagent_types — USE them.
- **Opus (this session) reserved for: genuine/security/architecture review + Operator interface.** e.g. #514 (cred seam) + #517 (worker-run) were Opus reviews; #515/#516 routine → sonnet.
- **DO NOT rebuild the ambient-cred tender.** I tried a raw tmux+host-codex+ambient-overwatch conveyor-tender — it VIOLATES mandatory containment + re-creates the 2026-06-25 ambient-credential authority-leak. Torn down. Charter parked at `.ce/state/parked/CONVEYOR_TENDER_CHARTER.parked.md`. The correct tender is the CONTAINED Integrator (#216) running with per-call injected creds — BLOCKED on the egress chain below.

## 🎯 PRIORITY: CONTAINED-CONTROLLER EGRESS CHAIN (the real fix — unblocks cheap modelless mechanics)
A contained controller/tender CANNOT push/enqueue yet (tokenless contained launch, #228/#495). The chain:
1. ✅ **#514/#240** (fail-closed `gh` credential SEAM) — MERGED (main 0b069a4). Guard shadows `gh`, refuses (exit 78, value-free) until transport deputy fills it.
2. 🔧 **#239** (wire approval-wall daemon → SecretIdentityBackend/OpenBao SUPPLIER that fills the seam) — **dev-4 building** (branch `ce239-wall-openbao-supplier`). TIGHTLY SCOPED: thread existing tested `approval_wall_secret_supplier_from_secret_identity_backend` + import secret_identity + test. NOT arming, no raw secret.
3. 🔧 **#237** (herdr authenticated Operator reach plane, retire `sudo docker exec`) — **dev-3 building** (`ce237-herdr-reach-plane`).
4. ⏭️ **#242** (contained-seat self-push via injected cred) — unblocks after #239.
→ Then a contained, per-call-cred-injected, MODELLESS Integrator runs the conveyor. THAT is the end state.

## FLEET (all foremen, Working)
- dev-1 → **#177** (Knowledge-SSOT drift-CI; `ce177-knowledge-ssot-drift-ci`).
- dev-3 → **#237** (herdr reach plane).
- dev-4 → **#239** (wall→OpenBao supplier).

## CONVEYOR (main 0b069a4) — ALL OPEN PRs APPROVED + DRAINING
#517(#259 worker-run), #516(#233 herdr-harden), #515(#166 slice-2), #507(#244 worker-tier), #498(#198 dogfood) — all APPROVED + auto-merge; queue draining. Merged this session incl: #504/#505/#506/#508/#509/#510/#511/#512/#513/#514.

## TICKETS FILED THIS SESSION
- **#259** ce worker run --role (governed launch-and-collect) — LANDING as #517 (first slice; deferrals: architect_research egress + capability reconciliation, both depend on #239/#240).
- **#260** D4 release-artifact hash drift + parity CI guard (served install.sh ≠ published SHA256SUMS; D1 policy-doc v0.1.0-vs-0.2.0; D3 "signed playbook" wording). + the install/release audit: site↔README↔code byte-identical; only signature = SSHSIG on llms-install.md; "signed playbook" = the agent-native signed install spec (NOT `ce playbook run`).

## NEXT ACTIONS
1. As #177/#237/#239 commit → harvest on SONNET workers → review (routine→sonnet reviewer / genuine→Opus) → enqueue. Retask seats with next arc units (foreman packets; base64-on-remote dispatch).
2. After #239 lands → #242 (contained self-push) → then build the contained Integrator (#216) and retire Opus/sonnet from mechanics entirely.
3. Hold Opus to genuine review + architecture + Operator interface. Mechanics → cron/sonnet. NO ambient-cred shortcuts.
4. Surface to Operator ONLY: autonomy canary, reserved R1-R6, auto-halt.

## STANDING AUTHORITY: G1-G5 granted, R1-R6 reserved. Operator driving turn-by-turn (no autonomous /loop armed).
