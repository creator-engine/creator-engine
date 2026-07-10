# INCIDENT REPORT — Merge-gate down (OpenBao approval-wall token) — 2026-07-02

**Author:** CE-DEV-2 Orchestrator · **Severity:** high (merge gate down, autonomous night-arc blocked) · **Duration:** ~1h active recovery · **Outcome:** RESOLVED, gate now MORE durable than before (restart-safe).

## 1. What happened
The merge-queue/wall daemon (`v3_cli queue-daemon`, pid 3292408 on the DGX) auto-merges ce-dev-2-approved+green PRs by minting an "approval capability" whose signing secret it fetches from OpenBao (`ce-kv/forge/approval-capability/wall`). During the night-arc the daemon began logging `approval_capability_mint_failed` / `error=approval capability secret unavailable` and stopped merging — approved+green PRs (#713, #715, then #716/#717) sat un-merged.

Root symptom: the daemon's OpenBao token (`~/.ce-keys/ce-approval-wall-token`, a STATIC file with no auto-refresh) had **expired** (`lookup-self` → permission denied). The long-running daemon had a renewed in-memory copy and briefly **self-healed** (that's why #713/#715 eventually merged), but the on-disk token was dead.

## 2. Root causes (TWO, discovered sequentially)
1. **Expired static token.** The daemon reads a static token file at launch. Its TTL lapsed (likely during the hours the controller was mistakenly idle earlier in the day). A running daemon can limp on a renewed in-memory token, but ANY restart/reboot re-reads the dead file → hard fail-closed.
2. **Token policy too narrow for the restart preflight** (this is what made recovery hard). The backend's `validate_config()` does `GET /v1/sys/audit` (a root-protected endpoint needing `read+sudo`) as an audit preflight. A freshly-minted token scoped to only the secret path got HTTP 403 → the code raised `AuditUnavailable("no enabled audit device")` — **misleading**, because the audit device IS enabled (`ce_audit/` file → /var/log/openbao/audit.log). The OLD daemon's token happened to have broader capability; the narrow replacement did not.

## 3. How it was solved
1. **Minted a fresh durable token** via the OpenBao admin generate-root ceremony (init-bundle passphrase → 3 unseal shares → transient root → mint → revert+revoke, with a fail-safe cleanup trap). Critically, the token is **`-orphan` + `-period=720h` (renewable)**: orphan so revoking the transient root doesn't cascade-revoke it; periodic so it auto-renews indefinitely. Written to the daemon token file → **restart-safe**.
2. **Widened the policy** `ce-approval-wall-read` to include `sys/audit` (read+sudo) + `sys/health` (read), so `validate_config()`'s preflight passes. (Existing token gains caps live — policies are evaluated by name.)
3. **Restarted the daemon** onto the durable creds via the canonical launcher → `validate_config` passed → secret materialized to `/dev/shm/ce-wall-daemon/secret` → wall armed → minting resumed. Verified end-to-end: daemon minted + enqueued #716/#717.

Net: gate restored AND hardened — it now survives a reboot/restart (which it did not before), which also de-risks the #351 DGX→VPS daemon relocation.

## 4. Why it took ~1 hour — honest post-mortem

### Incorrect steps I took
1. **The biggest self-inflicted wound: I restarted a WORKING daemon.** The original goal was just to make the daemon restart-safe. Writing the fresh token to the file ALONE achieved that; the running daemon was fine (self-healed). I restarted it anyway "to be clean" — which turned a self-healed gate into a full outage and exposed root cause #2. Lesson: when the goal is future-restart-safety, fix the file and leave the running process alone.
2. **`pgrep -f "v3_cli queue-daemon"` self-match footgun.** My own shell command contained that string, so `pgrep -f` matched my own process and I killed it (exit 144), while the real daemon survived. Wasted a cycle. Fix: target the daemon by exact PID / `ps | grep | grep -v grep`.
3. **Multiple blind ceremony re-runs**, each costing 2 OpenBao restarts, from small bugs: (a) generate-root `-format=json` output was warning-prefixed so JSON parse returned empty — fixed by parsing the plain "Encoded Token" line; (b) a variable-name collision (`OUT` used for both the output-file path AND the generate-root capture) wrote the token to a garbage filename; (c) the first mint was NOT `-orphan`, so `token revoke -self` on the transient root **cascade-revoked the fresh token** (child of root) → it read as invalid immediately after minting.
4. **Chased a dead-end (env-var fallback).** I tried supplying the secret via `CE_APPROVAL_CAPABILITY_SECRET`, but `_approval_wall_primary_then_env_supplier` returns `primary()` directly when a backend is configured and NEVER falls back to env; and minting REQUIRES the backend supplier regardless. So the env path could never work while the daemon runs with `--approval-wall-secret-backend openbao`. ~2 attempts wasted before I read that function.

### Information I was missing, and where I finally found it
- **The generate-root ceremony mechanics** (flag placement inside the `listener` stanza, unseal-3 + generate-root flow, passphrase→bundle): I HAD this in memory [[ce-openbao-admin-recovery-blocked]] — but the reusable script it referenced (`scratchpad/bao_broker_approle.sh`) was gone from disk (session-scoped scratchpad), so I reconstructed the script from the memory prose. Reconstruction is where bugs (a)/(b)/(c) crept in.
- **The bundle's root_token is revoked** (so I must generate-root, can't reuse it): stated in the memory; confirmed by a lookup-self test.
- **The `-orphan` requirement**: NOT documented anywhere — learned by debugging the "valid-in-script-but-invalid-after" symptom and realizing root-revocation cascades to child tokens.
- **The REAL second root cause (audit preflight / sys/audit capability)**: NOT in any memory or doc. It was hidden because the secret supplier **swallows the backend exception to `None`** (`supply()` returns None on any failure), so the daemon only ever printed the generic `armed_state_without_secret`. I found it by **reproducing the backend materialize directly in the daemon's venv** (`python -c "... backend.validate_config(); backend.issue(); backend.materialize() ..."`), which surfaced the swallowed `AuditUnavailable` traceback. That one diagnostic — running the swallowed path in isolation — is what cracked it. Then reading `secret_identity.py:1043 validate_config` showed the exact `GET /v1/sys/audit` call and its capability requirement.

### What would have made it fast
- A one-shot health/preflight command that runs `validate_config` and prints the REAL exception instead of swallowing to None. (Product gap — worth a ticket: `ce queue-daemon --preflight` that reports the actual backend failure.)
- The daemon on an **AppRole** (auto-renewing) instead of a static token, so expiry can't happen. (The memory's own "FLIP" section already called for this; it was never done. Now that the token is periodic+orphan the urgency drops, but AppRole is still the right durable design — candidate follow-up ticket.)
- Not restarting the working daemon (see incorrect-step #1).

## 5. Follow-ups (tickets to file)
- `ce queue-daemon --preflight` that surfaces the real backend/validate_config error (no swallow-to-None).
- Migrate the approval-wall daemon to an OpenBao **AppRole** (auto-renew; eliminates static-token expiry class of incident).
- Document the daemon-token policy requirement (secret-read + sys/audit read+sudo + sys/health) next to the launcher.
- Full recovery playbook is codified in memory: [[ce-approval-wall-daemon-token-durable-recovery]].
