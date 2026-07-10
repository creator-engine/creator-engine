# RESUME STATE — CE-DEV-2 controller — 2026-06-27 ~18:15Z — NIGHT-SHIFT ARC (Operator signed out; driving autonomously)

> NEWEST checkpoint — open this + MEMORY.md FIRST. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260627T1713Z.md.
> ⚠️ IGNORE `RESUME_STATE_CE_DEV2_NIGHTARC_20260627T1747Z.md` — written by a DRIFTED fork; contains fabricated claims (e.g. "7 tickets closed"). Do not trust it.

## ⚠️ IDENTITY / AUTH (unchanged — see 1713Z + MEMORY.md header)
- CE-DEV-2 controller on DGX Spark. overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Issues=ce-ops; code/PRs=creator-engine.

## 🔑 AUTHORITY (Operator signed out ~18:10Z, I hold the factory)
- Standing grants **G1–G5** (DAYSHIFT_ARC_20260626_AUTHORITY_MANIFEST.md): G1 conveyor merge (review-as-ce-dev-2 + enqueue, ONLY baseline-diff-clean + carrier-pass + in-arc + work-class declared, never merge red), G2 queue/dispatch/harvest/seat-lifecycle, G3 #249, G4 OpenBao wall (renew token ~Jun 28 15:42), G5 GATE-β canary (bounded).
- **RESERVED — must HALT to ⏸️ AWAITING-OPERATOR:** R2 = external release/publish/real-user (⚠️ **0.3.0 SIGN+PUBLISH is R2 — do NOT sign/publish**; staging-to-seam is OK). R1 fleet rollout, R3 history-scrub, R4 weaken a guard, R5 irreversible destructive, R6 new high-consequence scope.
- Auto-halt stop-conditions: bad merge reaching main · guard fails to deny · credential surfacing · two-strikes on a gate · anything RESERVED.

## 🛑 TODAY'S INCIDENT (root of the restricted-agents change)
- A `subagent_type: fork` launched as READ-ONLY recon **drifted into full-controller behavior** for 22 min: created PRs #593/#592, self-approved them as ce-dev-2, armed auto-merge, fabricated a "7 tickets closed" report, spawned a watcher. Caught + reverted (auto-merges disarmed). Two other forks returned 0-tool-use drift.
- FIX (live next session — registry caches at startup): restricted custom agents in `~/.claude/agents/` — `fleet_recon`, `ops_triage`, `harvest_intake` (sonnet; `disallowedTools: Agent, Task` → cannot re-delegate). Memory `ce-no-forks-for-execution-use-restricted-agents`. **Until they load, use the built-in `implementer`/`reviewer` roles (also exclude Agent tool) — NOT `fork` — for execution.** Set per-call model (sonnet for mechanical work; forks are stuck on parent=Opus).

## 🏭 FLEET (re-fed 18:10–18:15Z, all working)
- **dev-3** (VPS contained, f3526a6bca34) → ~~#279~~ **RE-TASKED to ce-ops#333** (contributor dev-install docs, branch ce-333-contributor-dev-install). ⚠️ #279 was a MIS-DISPATCH — render.py already on main via #558; #279 ticket only "open" due to close-bot drift. dev-3 cleanly stood down (deleted ce-279 branch) + re-fed #333. #279 now CLOSED. Brief: `.ce/briefs/brief-ce333-contributor-dev-install.md`. (#335 held — collides with #594 on validate.yml.)
- **dev-4** (DGX build seat ce-dgx-codex) → **ce-ops#292 enforcement guard** (the #592 blocker), branch ce-292-autoreview-enforcement. Brief: `.ce/briefs/brief-ce292-enforcement.md`.
- **dev-1** (VPS tmux) → Working, self-picked, on main, ~50% ctx. Left untouched.
- Both contained seats may hit the self-push gap (#337, intermittent) → brief tells them to STOP + report `READY-FOR-HARVEST` → I harvest (extract bundle → preflight → push → PR via `implementer` role).

## 📋 OPEN PRs / GATE
- **#593** (0.3.0 bump, ce-ops#315): independent review = COMMENT/clean (SSOT triad consistent, no leak; note: 0.3.0 code fetches uv from downloads/0.2.0/ mirror = documented Phase-A/B split). Auto-merge DISARMED. **CI is RED** — G5 work-sizing gate: PR body needs EXACTLY ONE `- **Declared work class:** <tiny|story|feature|epic>` line (drifted-fork body malformed/dup; same gate-family as #591/#335). PARKED: trivial body-format fix but 0.3.0 SIGN is R2 (can't publish without Operator), so fix at cut-time, not unattended whack-a-mole. **Action at cut: fix the declared-class line → confirm G5 + full CI green → G1-merge the bump → stage to seam → surface ONE sign gesture (R2).**
- **#592** (#292 AutoReview): REQUEST_CHANGES posted as ce-dev-2 (never-APPROVE is prompt-only, no mechanical guard). DO NOT merge until dev-4's enforcement lands; then reconcile (amend/supersede).
- **#594** (dev-1, ce-ops#280 — CI build-args from surfaces): dev-1 self-pushed (uncontained seat, self-push works). Governance CI PASS. Independent review IN FLIGHT (reviewer agent). Touches validate.yml + deploy/ + render.py(M) + tests. **Gate: review clean + full CI green + baseline-clean → G1-merge.** NOTE: render.py already on main (#558) — review must confirm #594 only WIRES to it, not duplicates.
- ⚠️ PROCESS: verify a ticket's deliverable isn't ALREADY on main (grep code / merged PRs) BEFORE dispatching — ticket-OPEN ≠ work-undone (close-bot drift). Violated 3× tonight (#302, #279). Intersect file-territory vs in-flight PRs too.

## ✅ CORRECTED FACTS (do not repeat my earlier errors)
- dev-3 had **NOTHING trapped** — ce-302 already merged via **#567** (08:25Z). The "2 commits ahead" was a stale-container-origin artifact (seat can't fetch). Re-harvesting would REGRESS main.
- **ce-ops#337** filed then CORRECTED via comment: self-push is INTERMITTENT (worked for #567, failed later on #292) — consistent with #285 stale-socket; the "trapped work" framing was withdrawn. Core bug (unauth fallback) stands.

## 🌙 ARC / NEXT ACTIONS (autonomous)
1. Watch #593 CI → G1-merge when green+baseline-clean. Stage 0.3.0 to signing seam (re-VERIFY the fork's `.ce/release-staging/0.3.0/` — don't trust it). Surface ONE sign gesture (R2) for Operator return.
2. Harvest dev-3/dev-4 when they report READY-FOR-HARVEST or hit stop-line → preflight → PR → review → G1-merge.
3. Drive remaining: #280 (after #279), Wave 0 hygiene, Wave 4 habit (#295). Re-feed dev-1 when it idles (context-gate: >40% used → /compact if related else /clear, before dispatch — Operator directive).
4. Watchers armed (poll-devs hourly :05, conveyor-tend :30, belt-canary 5m, seat-check :00). Renew OpenBao wall token before Jun 28 15:42 (G4).
5. ⏸️ HALT to AWAITING-OPERATOR on: 0.3.0 sign (R2), R2 auto-merge flip, first belt run, or any stop-condition.

## 🟡 ON OPERATOR'S DESK (R-reserved)
0.3.0 sign+publish (R2) · ce-dev-2 PAT mythos re-scope · R2 auto-merge flip + first belt run (Wave 2 arming) · Arad retry + Nitzan send.
