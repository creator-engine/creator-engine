# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (day-shift high-gear: 4 deliverables ready + backlog swept + egress relief)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_WEBUI_DISPATCH.md`. Read this + `MEMORY.md` first. **main HEAD = `03d3796d`** (post #283+#284 merges).
**VPS reach (DGX has NO `ce-dev-1` ssh alias):** `ssh ce@100.72.252.20` → `sudo -n -u <user> tmux capture-pane -p -t '<sess>:<win>.0'`. dev-3 active window is index **1** (`dev3-onboard:1.0`), not 0.

## ⚠️ NEW STANDING PRACTICES (this session)
- **Dispatch seats via prompt-pointer+SHA**, never long inline prompts ([[ce-seat-dispatch-prompt-pointer-sha]]): write brief→file→`sha256sum`→seed `Read <path> (sha256 <h>) and execute`. Contained dev-4: write under its bind-mount `…/ce-workspaces/creator-engine/tmp/` (= `/workspace/creator-engine/tmp/` inside).
- **Estimate at AGENT pace** (hours/days), not human-dev pace — Operator corrected me twice. The egress gateway is CE-built code, NOT gated on OpenShell.
- **dev-4 context-clear = `/compact` ONLY** (never C-c/`/quit` — codex is the container `Cmd`, both kill the container) ([[ce-dev4-dgx-spark-access]]).
- **Codex seats share ONE OpenAI account** → x5→x20 sub upgrade lifts all (Operator upgrading) ([[ce-codex-shared-account-subscription]]).

## 🎁 FOUR DELIVERABLES READY (all committed-LOCAL, survive /clear — courier/review/ratify each)
1. **#287 / #152 website v8.1** — H1 now `FULL AUTOMATION: FROM IDEA TO WORKING APP` (all-caps, centered) + conveyor caption REMOVED (message once). Commit `4e45b2aa` on `ce152-website-copy` (worktree `/home/cedev2/ce152-website-seat`, seat `ce-web152` idle). **Draft PR #287 already open** (`Closes ce-ops#152`). v8 snapshot retained. ▶ FINALIZE (Operator said to): re-capture a FRESH hero screenshot (existing `tmp/site-shots/*.png` PREDATE the H1 change) → force-push amended commit → un-draft → visual checkpoint → independent review (NOT ce-dev-2) → merge as overwatch.
2. **ce-webui / ADR-0008 web control UI** — commit `eb2dbc06` on `ce28-web-control-ui-adr` (worktree `/home/cedev2/ce-webui-design-seat`, seat idle, 47% ctx). ADR at **`docs/decisions/ADR-0008-*`** (NOT docs/architecture/adr — validated home) + mockups **`tmp/webui-shots/index.html`**. Recommends: #28 = umbrella, open 2 children **Web-A** (read-only mirror + cockpit-serve→WS gateway) + **Web-B** (binding-act seam, separate governance review). ▶ Operator review ADR+mockups → ratify → courier PR → dispatch Web-A/Web-B build.
3. **ce-cockpit / #45 Slice 2** — resolve-a-decision write-seam (canonical gate + form-echo). Commit `0b22c7fb` on `ce45-journey-cockpit-elevation` (worktree `/home/cedev2/ce-cockpit-seat`, idle), 15 paths, SVGs `tmp/cockpit-shots/05-resolve-form-echo.svg`+`06-inbox-after-resolve.svg`. Known red = 2 packaging tests (stale wheel → controller wheel-rebuild+SHA re-pin, +2→17 paths, ADR-0006). Rebases clean onto main. ▶ courier PR → **Slice-2 GOVERNANCE review** (distinct from visual) → wheel rebuild → merge.
4. **ce-egress / ce-egress-broker (ADR-0007 v0, #153 P0)** — commit `095f3527` on `ce-egress-broker` (worktree `/home/cedev2/ce-egress-broker-seat`, idle), 23 files. Deterministic fail-closed verify→mint seat App token→push+PR→audit. ▶ courier PR → review → CONTROLLER WIRING needed before live: host trust store (CE signing pubkeys in gpg/allowed_signers), per-seat PEM custody (/dev/shm), installation_ids (dev-2 set, dev-4=discover 141102698), fill `apps.example.json` (App ids + authorized_logins + namespaces), optional precondition hook.

## ACTIVE SEATS (still running)
- **dev-3** codex VPS (`dev3-onboard:1.0`) — **#109 Ring-1 §8c FS mediation** (Landlock cred-path deny), branch `ce109-ring1-fs-mediation`. Refreshed to 100% earlier; ⚠️ codex weekly ~15% (shared pool — upgrade pending). Its OWN ratified mandate (claim wclaim-37006f5c).
- **dev-4** codex CONTAINED DGX (`dev4stage1`, `ssh cedev4@localhost`) — **#154 cross-repo auto-close Action**, branch `ce154-autoclose`. NEVER C-c; courier via ce-forge-dev4 App (4085526/install 141102698/PEM /dev/shm), NOT the ce-dev-4 PAT (no push). Has done #119 (PR #286).
- **dev-1** codex VPS (`ce-dev1-orchestrator`) — finished #285 peer review = **CHANGES_REQUESTED**; likely idle now. Owes nothing pending; available.
- DGX seats `ce-webui`/`ce-cockpit`/`ce-web152`/`ce-egress` = DONE/idle (deliverables above).

## PR BOARD (main=03d3796d)
- **#283** ADR-0007 ✅MERGED · **#284** launcher ✅MERGED (CI-trigger-gap fix → #151).
- **#285** playbooks (author ce-dev-3) — **CHANGES_REQUESTED by dev-1**; dev-3 is on #109 → needs dev-3 to address review (interleave or after #109).
- **#286** [dev-4] #119 handoff-contract design — DRAFT, awaiting **Operator ratification of the contract shape** before merge-bound build.
- **#287** #152 website — DRAFT, H1 done, finalize pending (above).
- **#281** OpenBao secret-zero broker — DRAFT, CHANGES_REQUESTED, DIRTY → ce-dev-1 rework + rebase (the OpenBao P1 dependency of #153).

## TICKETS / BACKLOG (this session)
- Filed: **#151** (scoped re-review + CI-trigger-gap self-heal), **#152** (website, couriered), **#153** (egress-broker phasing P0→P1→P2), **#154** (cross-repo auto-close Action — dev-4 building it).
- **Backlog sweep DONE**: closed 12 fully-delivered ce-ops issues (#21,26,54,56,58,97,121,127,130,140,143,149) with 📦 provenance comments. **ce-ops 131→119 open.** 32 kept open (programs/arcs/in-progress), 0 false closes.
- Root cause of pileup = cross-repo (issues in ce-ops, PRs in creator-engine; GitHub auto-close is same-repo only) → #154 Action fixes it going forward.

## ⏸️ PENDING OPERATOR
1. **#287** finalize/visual-checkpoint (fresh hero shot needed) → review→merge.
2. **ADR-0008 web control UI** + mockups (`tmp/webui-shots/index.html`) review → ratify → dispatch Web-A/Web-B.
3. **#286 (#119)** handoff-contract shape ratification.
4. **cockpit Slice 2** governance review.
5. **`CE_OPS_TOKEN`** repo secret (ce-ops issues:write, least-priv) for the #154 Action when dev-4's PR lands.
6. Subscription **x5→x20** (Operator doing) · rotate leaked `ghp_…1XTgpz`.

## OPS NOTES
- **Fleet-watcher** `~/ce-fleet-watcher.sh` (last bg id b4bvlu9u9) — session-bound, won't notify a NEW session → **RE-ARM after resume** (`bash ~/ce-fleet-watcher.sh` run_in_background). It missed the 3 DGX completions this round (Working→idle detection gap — improve if reused).
- Pre-existing debt (ce-webui flagged): 4 historical carriers in `.ce/pr-manifests/` fail `path_manifest_hash_mismatch` under current normalization (immutable merged ledgers — awareness only).
- Briefs on disk: `/home/cedev2/ce-briefs/` (ce152-h1-refine sha `ea4bf09f…`, ce-egress-broker, web-control-ui-adr, playbooks-scaffold-build, etc.).
