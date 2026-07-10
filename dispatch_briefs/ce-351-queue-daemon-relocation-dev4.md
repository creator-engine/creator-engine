# SEED BRIEF — ce-ops#351: merge-queue/wall daemon → VPS, Restart=always — SEAT: dev-4

**Context (self-contained — embed; do not rely on reading the private ticket):**
The merge-queue/wall daemon (`v3_cli queue-daemon`) auto-merges ce-dev-2-approved+green
PRs. It currently runs on the DGX (a physical, reboot-prone box) launched by an ad-hoc
host script with NO restart policy. On 2026-06-28 the DGX rebooted and the daemon did
NOT come back — merges silently blocked until manually restarted. Fix: make the daemon a
**durable, boot-persistent service with Restart=always**, and prepare its **relocation to
CE-DEV-1 (Hetzner VPS)** where OpenBao + the overwatch GH token already live (co-locating
removes a cross-host dependency for the approval-wall secret).

**Branch:** `ce-351-queue-daemon-relocation` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely S/M).
**Repo:** creator-engine/creator-engine. You are a contained DGX seat: worktree under
`/var/tmp`, branch off `origin/main` (git fetch first), signal READY-FOR-HARVEST when done
(the controller harvests + does the live cutover — you CANNOT test systemd/VPS from here).

## Deliverables (committed artifacts + runbook — the controller performs the live cutover)
1. **systemd unit** `deploy/queue-daemon/ce-queue-daemon.service` — runs `v3_cli
   queue-daemon`, `Restart=always`, `RestartSec=5`, `WantedBy=multi-user.target` (boot
   persistence), sane `StartLimit*`, journald logging, and env wiring for the OpenBao
   approval-wall secret (`BAO_ADDR=https://100.72.252.20:8200`) + the overwatch GH token.
   Load secrets via an `EnvironmentFile=` pointer (a path, NOT secrets in the unit) or a
   documented `ExecStartPre` fetch — NEVER bake a token/secret into the committed file.
2. **Launcher** `deploy/queue-daemon/launch-queue-daemon.sh` — hardened successor to the
   current ad-hoc `~/ce-wall-daemon-launch.sh`: fail-closed if the GH token / BAO secret
   is missing (exit non-zero with an actionable message), a `--health` self-check mode
   (daemon alive + token valid), idempotent.
3. **Runbook** `deploy/queue-daemon/RELOCATION.md` — exact cutover steps (install unit on
   VPS as the dev-1 user, enable+start, verify a test approval auto-merges), the DGX
   retirement step, and a **rollback** (re-start on DGX) if the VPS instance misbehaves.
   Note the boot-persistence fix applies to WHICHEVER host it lands on.

## Constraints
- Do NOT put any secret/token value in a committed file — pointers/EnvironmentFile only.
  [[ce-228]] credentials never in container env/metadata.
- Do NOT touch the daemon's Python logic (`v3_cli queue-daemon`) unless a genuine
  boot/health bug is found — this lane is deployment packaging, not a rewrite.
- Config/infra diff (no app logic) → if the test-coupling gate fires, use the
  `CE-TEST-COUPLING-EXEMPT` marker in the PR body (legitimate for pure deploy artifacts).
- Paths: `deploy/queue-daemon/**`, `.ce/pr-manifests/ce-351-queue-daemon-relocation.md`,
  `.ce/changelog/ce-351-queue-daemon-relocation.md`. Nothing else.

## Evidence / DoD
- `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp).
- systemd unit passes `systemd-analyze verify` if available in-container; else note it in the runbook for controller verification.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; signal READY-FOR-HARVEST. Do NOT push/approve/merge.
