# RESUME STATE — CE-DEV-2 controller — 2026-06-27 ~11:30Z — DAY-SHIFT ARC + AUTONOMY-INFRA BUNDLE

> NEWEST checkpoint — open this + MEMORY.md FIRST. Supersedes the T0930Z checkpoint. Companions: design docs in `.ce/state/research/` — `CE_SUPPORT_AGENT_PLAN_`, `CE_DOC_AUTOGEN_DESIGN_`, `CE_AUTONOMOUS_RELEASE_DESIGN_`, `PLAYBOOKS_TO_SKILLS_PLAN_`, `DAYSHIFT_ARC_20260627_MANIFEST.md`.

## ⚠️ IDENTITY / AUTH / TOPOLOGY (read first)
- **CE-DEV-2 controller** on the DGX Spark (`spark-b824`, aarch64, `cedev2` uid1003, tailnet 100.100.105.50). Merge gate + Operator interface + foreman. ALL execution via WORKERS (no inlining — only approve+enqueue ratification, my own memory, and SECRET-CUSTODY stay inline). overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Code=creator-engine/creator-engine (PUBLIC); Issues+internal=ce-ops (PRIVATE).
- **Reviewer identity update:** `ubuntuaws745-cmyk` was RENAMED → canonical login is now **`ce-dev-2`** (same account, GitHub id 286082568; credential `~/.ce-keys/ce-dev-2.pat`).
- **AUTHORITATIVE dev-infra SSOT** = `ce-ops:infra/identity-registry.yaml` (merged ce-ops#307). MEMORY.md points at it; registry wins on conflict.

## 🛑 CONTROLLER-CHECKOUT POLLUTION — careful cleanup needed (do NOT naive-reset)
The controller checkout `/home/cedev2/creator-engine` is on branch `ce11-test-tier-split` with **HEAD = `0426e3cc`** (the skills slice) sitting on `46c91a0f` (ce-ops#11 test-tier-split). PLUS uncommitted: **`M validators/creator_engine_validator/cli.py`** + untracked worker-leftover worktrees (`.ce/wt-*`, `mcheck-wt/`, `.ce/briefs/`, `.ce/envelopes/`, `CEDEVSHERDR.md`). The skills work `0426e3cc` is ALREADY safely on PR #578 (head `567cf87a`, reconciled), so it's redundant locally. ON RESUME: (1) VERIFY `M cli.py` isn't needed real work (likely a stale worker-leftover; `git diff cli.py` — if it duplicates merged #576/#580 content, discard); (2) confirm skills are in #578; (3) then reset the branch cleanly (to `46c91a0f` / `origin/ce11-test-tier-split`). Workers branch off origin/main so this pollution isn't actively harmful, but clean it before relying on the local checkout. ce-ops#11 (test-tier-split, `46c91a0f`) is legit work to LAND eventually (queue it behind the egress/test PRs).

## 🎯 AUTONOMY-INFRA BUNDLE — Operator-ratified ("ship-and-document-yourself"), EXECUTING
Four epics filed + ALL FOUR first slices in the gate (each first slice G-grantable; the R-flips reserved):
- **#311 Support agent `ce ask`** → first slice **PR #580** (P0 foundations, honest scaffold, corpus reuses #571 guard) — APPROVED, merging. External exposure RESERVED behind the zero-leak eval.
- **#312 Doc-autogen / doc-freshness** → **PR #581** (`ce --help`→CLI ref, per-merge generate-then-verify, artifact in internal `.ce/reference/`) — review GOOD on all 5 technical points; body-fixed for the work-class papercut + retriggered → APPROVE on green.
- **#313 Autonomous release (CEO-mode)** → **PR #576** (Phase A stage-to-seam, no signing/publish, refusal intact) — APPROVED, merging. Phase B publish/sign = R-reserved (ce-root-v1 signing stays the Operator's one gesture).
- **#314 Playbooks→Skills** → **PR #578** (2 thin-pointer skills + anti-drift guard with teeth) — APPROVED (re-pushed after a mispush; CI re-running).
Designs all reduce to CEO-mode build+arm / Operator-holds-the-flip. The per-merge generate-then-verify (doc-autogen) + auto-merge (#561) + autonomous-release together = the autonomy loop.

## 🔑 KEYSTONE + ARC PRs
- **#575** SO_PEERCRED attestation (ce-ops#289) — APPROVED (adversarial review: parse correct, audit real, NON-BREAKING for legit seats, race-free), merging.
- **#577** belt observe-only (ce-ops#293) — ✅ MERGED. **#579** Arad runbook — ✅ MERGED.

## 👋 ARAD ONBOARDING — READY end-to-end
Install (one-liner, four-way-hash-verified current ✅) · Onboard (`ce verify-install`/`ce onboard` — user-facing kernel cmds, NOT cev3 ✅) · Co-drive first-PR: **PEM secured at `/dev/shm/mythos-ce-app.pem` (mode 600, validated; /tmp original shredded), ratified ✅**, env `~/.ce-keys/mythos-ce-app.env` staged (WORKDIR=~/ce-pilots/mythos, reviewer=ce-dev-2/ubuntuaws745-cmyk distinct from App-bot `mythos-ce[bot]`). Pilot repo `chmod735-dor/mythos`. **Only live act left = `openssl rand -hex 32` at the ratify step.** Operational runbook = `playbooks/controller/runbooks/arad-pilot.md` (#579, MERGED). NB `/dev/shm` is ephemeral — re-place PEM after reboot until OpenBao B1.
- **Welcome/onboarding package** = DRAFTING (worker aa2050e9, Opus) → public `docs/guide/**`, product-lens, for users + collaborators, with the verified Day-One UX (`ce launch` = your OWN agent governed+invisible; no native TUI; two rails; install≠instant-PR). Outward-facing → needs Operator content sign-off.

## 🧭 DAY-ONE UX (code-verified — for the welcome package + your awareness)
`ce launch` spawns a visible tmux pane running the user's OWN Claude Code/Codex, wrapped by CE's PreToolUse governance — invisible until it gates (then native "permission denied: <reason>"). No CE-native TUI (`ce hud` is an alias). First-run `ce onboard` (6 phases) ends by dropping into a governed pane. The aha = "my normal agent, but it refused the dangerous thing and told me why." BUILT + dogfooded.

## 🎫 TICKETS FILED THIS SESSION
Bundle epics #311-314; slices #315(release-A)/#316(doc-autogen)/#317(support-P0)/#318(skills); #309 (VPS seat venv, MERGED #573); #310 (deterministic-citations learning, MERGED #574); #319 (Arad runbook, MERGED #579); **#320 (agent-native install narration polish — product win)**. Plus dev-infra registry #307 (MERGED #308).

## 📌 LESSONS / RECURRING FOOTGUNS (the friction the bundle kills)
- The **carrier + work-class-in-body papercuts** hit nearly every bundle slice (#576 missing carrier, #577/#581 missing body work-class line) — workers' local preflight ≠ CI on these. Fix = doc-autogen + the preflight directive #303 + a candidate case-insensitive work-class check.
- **Workers committing to the shared checkout** (the #578 mispush → checkout pollution above) — reinforce isolated-worktree discipline; verify a slice's PR shows the RIGHT diff before gating.
- **Contained seats can't self-preflight** until the venv image fix (#573 dev-3 MERGED; **DGX sibling `deploy/dgx-runsc` still needs it for dev-4** — fast-follow). dev-4 has ~3 stale uncouriered worktrees (ce297/ce298 — already merged; verify-then-discard).

## ▶️ NEXT ACTIONS (resumed session)
1. Sweep gate: confirm #575/#576/#577/#578/#579/#580 merged; gate #581 on green (work-class fixed). Re-run any transient-CI reds.
2. Welcome-package PR (aa2050e9) → review + surface to Operator for content sign-off.
3. Clean the controller checkout (see 🛑 above) — carefully.
4. Bundle Wave-2: file/dispatch the NEXT slices per the 4 epics (doc-autogen Tier-2 fleet-reconciler #C, release Phase B = R-reserved, support-agent P1 pilot, skills phase-2). Land ce-ops#11 test-tier-split. DGX env fix for dev-4.
5. dev seats: dev-1 idle (post #289/#300), dev-3 idle (relaunch on rebuilt image — worker af4c9ae6 was doing this; VERIFY it succeeded + dev-3 can self-preflight), dev-4 idle (needs DGX env fix). Re-feed as the bundle Wave-2 dispatches.

## 🔒 RESERVED TO OPERATOR (R-series)
First LIVE auto-merge flip (R2) · first unsupervised belt run · release publish/sign flip (ce-root-v1) · push-side fleet switch · granting any agent APPROVE / weakening the wall · external release of `ce ask` (post zero-leak eval) · external release beyond Nitzan/Arad · history-scrub.
