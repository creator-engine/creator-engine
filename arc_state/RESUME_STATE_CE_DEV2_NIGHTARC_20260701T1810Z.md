# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-01 ~18:10Z (NIGHT-ARC, autonomous)

> NEWEST. Supersedes day-arc 0745Z. Open with MEMORY.md + NIGHTARC_MANDATE_CE_DEV2_20260701.md + [[ce-nightarc-20260701-batch-ratified-authority]]. Arc BATCH-RATIFIED FULL (G-N1..G-N7; code≤M needs 2-review quorum; conveyor full auto-gate). Drive to completion; auto-halt→Operator on RESERVED.
> ⚠️ CONTEXT NOTE: harness window is ~1M tokens (NOT 200k) — do NOT self-throttle at "80-90%"; that was a false ceiling that idled the fleet for hours. Use /context to check real usage.

## ✅ DONE THIS BLOCK (night-arc opening)
- Closed day-arc leftovers: **#714 closed** (redundant — ce-ops#347 already done by #641; ce-ops#347 CLOSED). **#713 (triage auto-labeling) APPROVED** (2-review quorum: functional + mutation-safety, both APPROVE) → merging.
- Night-arc mandate written + batch-ratified (full).

## 🔄 IN-FLIGHT — 4 parallel lanes (I hold the gate)
- **dev-1** → **ce-ops#382** brain-drift false-RED fix (ce_brain_drift.py; scoped OFF pr_preflight). Branch ce-382-brain-drift-falsered. self-pushes PR.
- **dev-3** → **ce-ops#373** subprocess timeouts (pr_preflight.py + onboard_apply_live.py). Branch ce-373-subprocess-timeouts. Harvest when READY.
- **dev-4** → **N1 CONVEYOR GO-LIVE** (new conveyor_daemon.py: daemon-loop + arming envelope + side-effect ledger on prepare_harvest/land_bundle; default DISARMED). Branch ce-conveyor-golive. Harvest when READY.
- **implementer worker ab14f6a9** (worktree) → **#351 launcher arg-parity fix** (branch ce-351-launcher-argparity). Harvest via its worktree when done.

## ⛔ #351 CUTOVER DEFERRED — real finding (do NOT cut over until fixed)
The #710 launcher `deploy/queue-daemon/launch-queue-daemon.sh` OMITS `--approval-wall-secret-ref-policy-sha` (`c5de2d359286c1c3160a0ef553ebb2e7c19177bcec0c09c0be75a12d5d3ffa7a`) that the LIVE DGX daemon passes — without it the VPS daemon likely fails to fetch the approval-wall secret → silently blocks ALL merges. Fix in flight (worker ab14f6a9). **DGX daemon stays live meanwhile (merges flowing).** After the fix lands + review: STAGE non-destructively on VPS (install unit + env from the live values below + `systemd-analyze verify` + `--health`), then destructive cutover (stop DGX, enable VPS, verify test-PR auto-merge, retire DGX; rollback per RELOCATION.md).
- Live daemon env (for the VPS /etc/creator-engine/ce-queue-daemon.env): GH_TOKEN=overwatch (~/.ce-keys/overwatch.env $CE_OVERWATCH_PAT); BAO_TOKEN=`cat ~/.ce-keys/ce-approval-wall-token`; BAO_ADDR=https://100.72.252.20:8200; BAO_CACERT=/usr/local/share/ca-certificates/ce-openbao-ca.crt (present on VPS); CE_OPENBAO_KV_MOUNT=ce-kv; authorized-reviewer ce-dev-2; policy-sha 79b9dc8b…; secret-ref-policy-sha c5de2d35…; secret-path forge/approval-capability/wall; field signing_secret. VPS: sudo=passwordless, checkout /home/ce-dev-1/creator-engine, systemd 259.

## ⏭️ NEXT ACTIONS
1. Confirm #713 merged. Harvest dev-4 conveyor + dev-3 #373 when READY → 2-review quorum (code) → gate. dev-1 #382 PR → 2-review → gate.
2. Harvest worker ab14f6a9 launcher-parity → review → gate → THEN #351 staged cutover.
3. Surface-B strangeLoop (G-N4) — broker `--run-mode strangeLoop` already on main (#641); run the scoped autonomous-approve demo + promote to standing.
4. Keep seats saturated (G-N5, probe not-already-landed FIRST): next lanes from N2 (forge work-driving), N3 (#370/#368 validator), N4 (#339/#184/#369/#337), N5 (#367/#320/#166).
5. Conveyor arming (G-N3) once conveyor_daemon lands + verified.

## KEY FACTS
- Auth: overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve ce-dev-2 `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`.
- Contained-seat drive: `sudo docker exec ce-dgx-codex bash -c "HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr <cmd> w1:p1"` (dev-4 local); `ssh dev1 'sudo docker exec ce-vps-codex bash -c "…"'` (dev-3). Clear codex composer w/ C-u before re-dispatch (leftover text mangles the pointer — hit dev-1 tonight).
- 2-review quorum for code≤M (D-N1); docs XS/S single-review. Harvest contained via git-bundle; validate on DGX host venv PYTHONPATH=validators.
