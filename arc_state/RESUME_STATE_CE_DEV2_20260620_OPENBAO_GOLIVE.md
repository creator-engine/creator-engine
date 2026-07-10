# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (OpenBao go-live + night-shift wrap)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Saved at Operator request before context-clear (was 72%). Read this + `MEMORY.md` first.

## SEAT → HOST → REACH
- **dev-1** codex ctrl, VPS — `ssh ce@100.72.252.20` → tmux `ce-orchestrator:codex-ctrl`. Authors as **`cedev1vps-cmd`** (wired). ⚠️ The `ce` account on the VPS **no longer has passwordless root** (locked down for the OpenBao host — see below); it can only `sudo -u ce-dev-1/3/4` for seat mgmt. Root now needs the Operator's root password (`su -`).
- **dev-3** codex ctrl, VPS — `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Authors+reviews as **`ce-dev-3`**.
- **dev-4** codex ctrl, CONTAINED gVisor, LOCAL — `ssh cedev4@localhost` → tmux `dev4stage1`. Authors as **`cedev4vps-coder`** (commit-author wired). ⚠️ Container CANNOT push or run `gh` (no CI/ticket visibility) → controller publishes its branches via forge token (commit-and-signal pattern). NEVER C-c.
- **Me** dev-2 = `cedev2` (DGX). Author identity = **`ubuntuaws745-cmyk`** (git-config per commit; NO push token on DGX — laptop-bound). Creds: `~/.ce-keys/mint-forge-token.py` (forge push), `~/.ce-keys/overwatch.env` (`CE_OVERWATCH_PAT`/`CHMOD_OVERWATCH_PAT`, both=**chmod735** = devops/merge automation ONLY), `ce-root-v1` (signing).

## ▶ IMMEDIATE NEXT ACTION
**Merge #275 (OpenBao go-live PR).** dev-3 was doing the FINAL review (config fixes) when state saved. On `DEV3 275-REVIEWED approve` + CI green: resolve review threads (GraphQL `resolveReviewThread`, branch protection requires conversation resolution), bring branch up-to-date (`gh api -X PUT .../pulls/275/update-branch` if BEHIND), then **squash-merge as `chmod735`-overwatch** (`GH_TOKEN=$CE_OVERWATCH_PAT gh pr merge 275 --squash`). #275 head was `83b095d7`, CI green, 4 commits, last author cedev1vps-cmd. The OpenBao items 2-5 are DONE so the merge gate is clear.

## 🔐 OpenBao GO-LIVE — COMPLETE (ce-ops#113 items 1-5)
**LIVE on the VPS.** Operator did all trust-root acts 2026-06-20 this session:
- Host = `ce-dev-1.tailf3cfef.ts.net` / `100.72.252.20`, bind tailnet-only, **OpenBao v2.5.5** at `/usr/local/bin/bao`, systemd `openbao.service`, config `/etc/openbao/openbao.hcl`, internal CA mTLS at `/etc/openbao/tls/` (CA key root-only 0600; ce-readable CA copy at `/home/ce/openbao-ca.crt`).
- **DONE:** 3-of-5 Shamir init + unseal (Operator-custodied shares, NOT on box/chat); KV-v2 at `ce-kv/`; approle auth; 4 per-dev least-privilege policies+AppRoles (`ce-dev-1..4`, path `ce-kv/data/devs/<dev>/runtime/*`, NO wildcard); fail-closed file audit (`ce_audit/`); restore-drill PASS; **root token revoked** (regenerate via `bao operator generate-root` + 3 unseal keys if ever needed). No auto-unseal (deliberate).
- **Host hardening (lockdown):** root password Operator-held; `ce` sudo scoped to `(ce-dev-1,ce-dev-3,ce-dev-4)` only (`/etc/sudoers.d/10-ce-seat-mgmt`); blanket cloud-init root grant removed; `ce` out of `sudo` group. Agent cannot reach host root → cannot read unsealed vault memory.
- **Bringup scripts staged** at `/home/ce/openbao-bringup/` (render-dev-policy.sh, setup-dev-roles.sh, restore-drill.sh — ce-readable, run as root).
- **3 OpenBao-2.5.5 config bugs found via live dogfood, fixed in #275 by dev-1** (+ regression smoke): (1) `disable_mlock=false` rejected by 2.5.5; (2) audit needs `options = {` map not `options {` block; (3) declarative audit not loaded at first boot — needs reload/SIGHUP (upstream openbao#2168).
- **DEFERRED runtime step:** secret-zero mint per dev (response-wrapped SecretID) happens when wiring each dev SEAT to OpenBao (broker not built yet); RoleIDs already exist.

## ⏸️ PENDING OPERATOR (from morning briefing)
1. **Account renames** → `ce-dev-N` / `ce-overwatch` pattern (UI-only, Operator). Then I re-cut CODEOWNERS v2 + re-point all seat git/gh configs + SSOT ce-ops#137.
2. **dev-2 + dev-4 push credentials** — dev-2 needs `ubuntuaws745-cmyk` token on DGX (laptop-bound); dev-4 container needs push+gh tooling.
3. **OpenClaw findings** comparison vs plan — report at `.ce/state/research/OPENCLAW_CE_RESEARCH_20260619.md`; top-5 already folded into #274 §8 (merged).
4. **OpenBao broker/secret-zero wiring** (when ready to connect dev seats to the vault).

## NIGHT-SHIFT (2026-06-19 PM → 06-20) — shipped, full log in ce-ops#139
Arc G1-G5 done (#274 program plan+OpenClaw §8, CODEOWNERS→4-equals #276, dev-4 wired, 31 CRIT tickets→milestone, reconciliation). Conveyor shipped #130(#277)/#140(#279)/#97(#278). Tickets opened: **#136** (/goal research), **#137** (SSOT identity registry), **#138** (first-class review in CE), **#139** (arc log), **#140/#141** (docs). main HEAD ~`2f4f2850`.

## OPS NOTES
- **All night-shift crons CANCELLED** (Operator request) — no autonomous watcher running; fully interactive.
- Memories written this session: [[ce-github-identity-model]], [[ce-review-model]], [[ce-bake-gaps-into-ce-not-conventions]] (+ MEMORY.md index).
- Merge mechanics learned: branch-protection needs conversation-resolved + up-to-date; use `resolveReviewThread` GraphQL + `update-branch` API, then overwatch squash-merge.
