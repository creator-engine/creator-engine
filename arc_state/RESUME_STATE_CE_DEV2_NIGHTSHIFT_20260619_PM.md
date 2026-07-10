# RESUME STATE — CE-DEV-2 Controller · 🌙 NIGHT-SHIFT 2026-06-19 PM

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Read this + `MEMORY.md` first. **Entry point at bottom.**

## SEAT → HOST → REACH
- **dev-1** codex ctrl, VPS — `ssh ce@100.72.252.20` → tmux `ce-orchestrator:codex-ctrl`, clone `/home/ce/creator-engine`. NOW authors as **`cedev1vps-cmd`** (git config wired; gh default via reviewer.env). Running session keeps old env until relaunch.
- **dev-3** codex ctrl, VPS — `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Authors+reviews as **`ce-dev-3`** (clean).
- **dev-4** codex ctrl, CONTAINED gVisor, LOCAL — `ssh cedev4@localhost` → tmux `dev4stage1`, clone `/home/cedev4/ce-workspaces/creator-engine`. Account `cedev4vps-coder` (token NOT on seat; only App env). **NEVER C-c.**
- **Me** dev-2 = `cedev2` (DGX). Author identity = **`ubuntuaws745-cmyk`** (set git config per-commit; NO push token on DGX — laptop-bound). Creds: `~/.ce-keys/mint-forge-token.py` (forge App push), `~/.ce-keys/overwatch.env` (`CE_OVERWATCH_PAT`/`CHMOD_OVERWATCH_PAT`, both=**chmod735** overwatch → merge mechanics only), `ce-root-v1` (signing).

## IDENTITY MODEL (see [[ce-github-identity-model]] / SSOT ce-ops#137)
4 devs author as own user accounts (cedev1vps-cmd / ubuntuaws745-cmyk / ce-dev-3 / cedev4vps-coder); chmod735 = overwatch/devops automation (merge/triage). Reviews = a SEPARATE dev + INLINE comments ([[ce-review-model]], product fix = ce-ops#138). **Renames to `ce-dev-N` / `ce-overwatch` = OPERATOR'S TOMORROW; tonight use current handles.**

## 🌙 NIGHT-SHIFT ARC = ce-ops#139 (ratified grants G1-G5)
- **G1** merge #274 (v3.5 plan + OpenClaw §8): dev-1 code-owner approves → overwatch squash-merge.
- **G2** drive #275 review loop (dev-1 per-dev-policy fix → dev-3 inline re-review → merge-READY); **HOLD merge** (Operator items 2/3).
- **G3** GitHub reconciliation (labels/milestone/close-stale/file-docs-tickets).
- **G4** wire dev-4 commit-author → cedev4vps-coder.
- **G5** CODEOWNERS → 4 equals (current handles): `* @cedev1vps-cmd @ubuntuaws745-cmyk @ce-dev-3 @cedev4vps-coder`; PR by dev-2 → dev-1 approves → overwatch merge.

## ⏸️ HELD — Operator only
#275 items 2/3 (Shamir/secret-zero/restore-drill) → #275 FINAL MERGE · account renames · dev-2 push token (drop `ubuntuaws745-cmyk` token on DGX to fully wire dev-2).

## BOARD
main HEAD pre-night = `facff85e`. Open PRs: **#274** (plan, CI green, dev-3 approved but CODEOWNERS needs dev-1 → G1), **#275** (OpenBao, CHANGES_REQUESTED by dev-3, dev-1 fixing → G2). Research report surfaced: `.ce/state/research/OPENCLAW_CE_RESEARCH_20260619.md`. Tickets opened this session: #136 (/goal↔strangeLoop), #137 (SSOT registry), #138 (first-class review), #139 (this arc).

## CONVEYOR-BELT MANDATE (Operator sign-out 2026-06-19 PM)
Keep dev-1/3/4 busy. When a seat idles with no arc task, dispatch ONE vetted ticket → governed loop (author → different-dev inline review → CI → code-owner approval → overwatch merge). **VETTED POOL ONLY:** ce-ops#97, #98, #130, #140, #141. NEVER: security/Ring-1/OpenBao/containment, architecture/decisions, pitch-critical-complex, held items. Full mandate + guardrails = ce-ops#139 log.

## ▶ RESUME ENTRY POINT
1. Re-arm the **~40-min** night watcher cron (`7,47 * * * *`) driving arc #139 + conveyor belt (CronCreate; session-only — gone after clear; prior id 52b835b3). 2. Verify reach to 3 seats. 3. Resume G1-G5 + any in-flight dispatched tickets from the #139 log's last entry. 4. Surface any ⏸️ to Operator FIRST.
