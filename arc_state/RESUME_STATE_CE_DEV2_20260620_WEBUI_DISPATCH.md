# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (web control UI design dispatched · 4 seats live)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_IDENTITY_ROLLOUT.md`. Read this + `MEMORY.md` first. **main HEAD = `28e57111`** (post #283 merge).

## ⚠️ #1 PENDING OPERATOR — two ratifications will land
- **Web control UI ADR** (from the `ce-webui` seat) — ADR + visual mockups + sliced build plan; ratify it, then dispatch the BUILD (Web-A read-only mirror → Web-B discharge-binding-act over the gate). Mockups will be under `/home/cedev2/ce-webui-design-seat/tmp/webui-shots/` → another **visual checkpoint** (design-green never self-assessed).
- **Cockpit Slice 2** (governance write-seam) — when the `cockpit` seat finishes, it needs a **governance review** distinct from the visual one (it deliberately breaks the cockpit no-write law by actuating the canonical gate via form-echo).

## SEAT → HOST → REACH (4 LIVE)
- **Me dev-2** = `cedev2` (DGX). gh NOT logged in — per-command `GH_TOKEN`. Creds `~/.ce-keys/`: `ce-dev-2.pat`(own, Issues:write✓), `ce-dev-4.pat`(HELD, dev-4 model-b), `overwatch.env`(`CE_OVERWATCH_PAT`/`CHMOD_OVERWATCH_PAT`=ce-overwatch, repo-scoped only), `ce-forge-app.json`+pem, `ce-root-v1` signing. VPS reach (DGX has NO `ce-dev-1` ssh alias) = **`ssh ce@100.72.252.20`** then `sudo -n -u <user> tmux ...`.
- **`ce-webui` seat** (DGX): tmux **`ce-webui`**, worktree `/home/cedev2/ce-webui-design-seat`, branch **`ce28-web-control-ui-adr`**, claude **Opus 4.8 xhigh + frontend-design plugin** (launched `--setting-sources user,project` — see [[ce-governed-seat-user-plugin-launch]]). DESIGN PASS: web control UI ADR + mockups + sliced plan (NO build). Brief: `/home/cedev2/ce-briefs/web-control-ui-adr.md`. Ref: ce-ops#28 (home) + #45 (journey reqs).
- **`cockpit` seat** (DGX): tmux **`ce-cockpit`**, worktree `/home/cedev2/ce-cockpit-seat`, branch `ce45-journey-cockpit-elevation`, Opus 4.8 xhigh. Slice 1 DONE+green-lit (commit `574993c2`). **NOW building Slice 2** (interactive write-seam → canonical gate + form-echo). Brief: `/home/cedev2/ce-briefs/ce45-journey-cockpit-elevation.md`. WHEELHOUSE FOLLOW-UP owed (rebuild wheel + re-pin SHA, manifest +2→14 — release-time, not the seat's job).
- **dev-1** = `ce-dev-1` OS user (uid 1004) on VPS — `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. codex gpt-5.5 xhigh. Finished **#281** (pushed + re-requested dev-3). **NOW on #284 conflict-rebase** (brief `/home/ce-dev-1/ce-briefs/284-conflict-rebase.md`).
- **dev-3** codex, VPS — `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Building **#145 playbooks scaffold** on `codex/ce145-playbooks-scaffold` (validator + CI gate + contracts + first playbooks). Brief `/home/cedev2/ce-briefs/playbooks-scaffold-build.md`.
- **dev-4** codex, CONTAINED gVisor, LOCAL DGX — `ssh cedev4@localhost` → tmux `dev4stage1`. NEVER C-c. Courier its forge ops via held `ce-dev-4.pat` (ADR-0007 model-b).
- **Reviewer seat** — RETIRED.

## PR BOARD (main=28e57111)
- **#283** ADR-0007 — ✅ **MERGED** (squash, base-only rebase, approval survived).
- **#284** launcher (ce149) — APPROVED but **DIRTY** post-#282 → **ce-dev-1 conflict-rebasing now**; rebase will dismiss approval → needs **scoped re-review** (#151). Do NOT hand-resolve hashes.
- **#281** OpenBao broker (ce135) — still **draft + CHANGES_REQUESTED**; ce-dev-1 pushed fixes + re-requested dev-3. Needs mark-ready + dev-3 re-review (dev-3 busy on #145).

## WEB CONTROL UI — the new flagship (ce-ops#28/#45, Operator's "real cherry" 2026-06-20)
Model = **OpenClaw control UI** (`docs.openclaw.ai/web/control-ui` + `openclaw/openclaw` `ui/`): a Vite+Lit+TS SPA served by the Gateway over **WebSocket RPC**, Tailscale-Serve auth, PWA. Maps 1:1 onto CE's agnostic-core: web = the **web L3** over the existing L2 read-model. **~80% already exists**: `cockpit_readmodel.py` (L2), `cev3 cockpit --json` (parity), **`cockpit-serve` LIVE on CE-DEV-1 :8200** (the gateway evolves from this), tailnet-native auth. Gap = the SPA + WS-gateway upgrade. ADR recs (seat adjudicates vs real code): stack=Vite+Lit+TS, gateway=evolve cockpit-serve (WS+RPC+static), auth=Tailscale Serve identity. HARD LAW: web computes nothing, writes only via the canonical gate (form-echo). Slices: Web-A read-only live mirror → Web-B discharge over gate.

## ▶ IMMEDIATE NEXT ACTIONS
1. Monitor **ce-webui** → ratify ADR + mockups (visual checkpoint) → dispatch Web-A build.
2. Monitor **cockpit** Slice 2 → governance review when green.
3. Monitor **ce-dev-1** #284 → when green, scoped re-review (#151) → merge (overwatch).
4. **#281** → once ce-dev-1's fixes are in + a reviewer free → mark ready + re-review → merge.
5. **dev-3 #145 playbooks** → review PR when up.

## ═══ DELTA (day-shift pace push, ~7% ctx handoff) ═══
- **#284** conflict-rebase DONE by ce-dev-1 (head `fa1e1c3a`, base 28e5711; prior ce-dev-2 approval at head `01af5fdf` dismissed). **dev-3 is scoped-re-reviewing it now** (#151 procedure, brief `/home/ce-dev-3/ce-briefs/review-284-scoped.md`).
- **#285** = dev-3's playbooks scaffold (ce145), OPEN + CI green, BEHIND (base-only). **ce-dev-1 is peer-reviewing it now** (brief `/home/ce-dev-1/ce-briefs/review-285-playbooks.md`). Cross-review = no self-review.
- **dev-4** = fully IDLE/available (strongest contained seat). #152 was only FILED, never implemented. Stale untracked in its tree: `.wave1-*.md`, `deploy/`.
- **▶ BOTH DISPATCHES DONE (2026-06-20):**
  1. **#152** → **`ce-web152`** Opus seat (DGX, worktree `/home/cedev2/ce152-website-seat`, branch `ce152-website-copy`). Brief `/home/cedev2/ce-briefs/ce152-website-copy.md`. Honors v3 site-archive snapshot + ledger; screenshot → `tmp/site-shots/`. On green: controller couriers PR → **Operator visual checkpoint**.
  2. **dev-4 → #119** (WHAT/HOW keystone: `tasks.ce.yml` handoff contract + `do_not_replan` SHA-binding) — **DESIGN PASS** on branch `ce119-tasks-handoff-contract` in `/workspace/creator-engine`. Deliver: `docs/architecture/tasks-handoff-contract.md` + `schemas/tasks.schema.yaml` + optional prototype. 🔒 in-compose lock posted on #119. **Binding contract shape returns for Operator ratification before any merge-bound build.** (Backup ticket if rescoped: #89 review-spawn bug — also clean.)
- **#284 ✅ MERGED** (12:00Z) — dev-3 scoped re-review was clean; real blocker was a CI-trigger gap (force-push to head `fa1e1c3a` fired no check-run despite content-identical to CI-green `be08b05f`). Fix: controller close/reopen → CI green → dev-3 APPROVED → merged. **Recurring-gap fix folded into #151** (re-trigger before blocking on CI) + flagged for the #145 reviewer playbook.
- **#285** still needs dev-1's peer-review verdict → then merge as overwatch (base-only rebase if BEHIND).

## FULL FLEET (6 seats live, 2026-06-20 day-shift)
1. `ce-webui` (DGX) — web control UI ADR+mockups · 2. `ce-cockpit` (DGX) — #45 Slice 2 write-seam · 3. `ce-web152` (DGX) — #152 website copy · 4. dev-1 (VPS) — peer-review #285 · 5. dev-3 (VPS) — scoped re-review #284 · 6. dev-4 (DGX contained) — #119 keystone design.

## ⏸️ PENDING OPERATOR
- Web control UI ADR ratify + mockup visual checkpoint (#1). · Rotate leaked `ghp_…1XTgpz`. · (optional) owner-account PAT w/ `organization_personal_access_tokens:read` for the #137/#147 audit.
