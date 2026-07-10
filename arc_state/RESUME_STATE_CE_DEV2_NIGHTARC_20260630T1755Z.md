# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-ARC — 2026-06-30 ~17:55Z

> NEWEST. Supersedes the day-arc 1600Z resume. Open this + MEMORY.md FIRST. **Night-arc mandate = `NIGHTARC_MANDATE_CE_DEV2_20260630.md`** (read it — lanes N0–N5). Standing authority G1–G7 + R1(Option A) + R5(install-spec re-sign) carry over.

## ✅ SHIPPED THIS (DAY) SESSION — 7 PRs
#687 (dev-4 surface fix), #688 (#375 scope-impact), #689 (#374 docs overview), #690 (#379 work-class choices), #691 (#380 DGX launcher guard), #692 (#67 L3 triage P0) — **MERGED**. **#693** (L4 brain launch-hydration fallback) — APPROVED+CLEAN, daemon merging. main = 1465aa8e3 (#692). Plus: **dev-4 HEALED** (codex device-auth re-login). Tickets filed: ce-ops#377/#378/#379(fixed)/#380(fixed).

## 🔴 FIRST NIGHT-ARC ACTIONS (in order)
0. **N0 automation-completeness audit** — dispatch recon/architect to map every automation lane (built/partial/not-started + finish-step). Drive from it.
1. **N1a — finish the PARKED install-spec re-sign** (R5 authorized). Worktree `.ce/wt-resign-llms` (branch origin/ce-L1-install-doc-fix, HEAD 10f824a5). Canonical sha256 `865ba4f46acaeb999064ecf9d719e22c216ffa5f75f96b93c0ee50c76122820e` (VERIFIED via `v3_installer.canonical_spec_bytes`). Sign w/ `~/.ce-keys/ce-root-v1` (passphrase `~/.ce-keys/ce-root-v1.pass` via SSH_ASKPASS) → embed value+content_sha256 (`release_publish._replace_field`; canonical strips them so safe) → verify (`ce verify-install`+guard+`ssh-keygen -Y verify` vs `.pub`) → ship to main (review+approve) → SHOW Operator diff. Then N1b redeploy live (mechanism UNKNOWN — investigate; main==live==0.3.1 already).
2. **N2 — L2 automerge GO-LIVE (Option A authorized)**: L2 harvest PR opening (worker a816f0a2 on final preflight) → SAFETY review → CI green → approve→merge = docs-class auto-merge LIVE. Spot-check first auto-merge. [[ce-l2-automerge-golive-decision]]
3. **N1.5 — render 6 human-facing public docs to HTML** (pitch-critical; site #docs = 1 HTML + 7 raw .md). Keep llms-install.md as machine .md.

## 🩺 SEATS (all idle, authed, healthy)
- **dev-1** (non-contained, self-push): idle. Doc-fix prep DONE → branch ce-L1-install-doc-fix (parked for N1a re-sign). Good for N1c e2e re-run.
- **dev-3** (contained ce-vps-codex, fetch-egress YES, push-needs-harvest): idle. Just shipped L4 (#693). ~0% ctx (compacted).
- **dev-4** (contained ce-dgx-codex DGX, HEALED, fresh ACCT B quota, strongest): idle. Just shipped L2 (harvesting). **Launch rule: ALWAYS explicit `CE_DGX_IMAGE=creator-engine/codex-runsc:0.142.4-aarch64`** ([[ce-dev4-rebuild-and-launch-canon]], ce-ops#380).

## 🤖 AUTOMATION — UNFINISHED (verify in N0; drive in N2)
Auto-merge canary built→GO-LIVE pending + P1 (kill-switch CLI, single-PR gate). Autonomous-approve (Surface B broker run-mode) coded but NOT deployed. L3 triage merged but DRY-RUN only (needs ce-ops#67 sentinel + apply flip). **L7 auto-releases NOT built (biggest gap)**. L1.b auto-track-main/auto-update (#366 ratified, #682 P0 merged — verify). Conveyor/intake still MANUAL. Close-bot #262 (verify). Queue/gate daemon LIVE ✓.

## 🔴 NEEDS OPERATOR
- **R4** — Nitzan's GitHub handle + scope (N1e contributor path).
- Spot-check first live auto-merge (N2); eyeball install-spec diff before merge (N1a).

## DAEMONS / WORKTREES
queue-daemon PID 43010 alive (2d). Monitors b9aipnn3b/bh8s12igt + dev-3/4 seat monitors alive. Worktrees to PRUNE (N5): `.ce/wt-ce690..693-review`, `wt-*-harvest`, ~210 stale — **KEEP `.ce/wt-resign-llms` until N1a ships**.

## KEY LESSONS THIS SESSION (new memories)
[[ce-contained-seat-completed-but-unpushed-not-stalled]] · [[ce-l2-automerge-golive-decision]] · [[ce-dev4-rebuild-and-launch-canon]] (CE_DGX_IMAGE-explicit). Misread guard: verify origin/main not the local rc2 checkout (the 0.3.0-vs-0.3.1 false alarm).
