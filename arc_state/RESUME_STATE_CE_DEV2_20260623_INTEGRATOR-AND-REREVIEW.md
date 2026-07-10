# RESUME STATE — CE-DEV-2 · 2026-06-23 · 🏗️ Integrator program + forge.re_review (TOP) + onboarding-wave reviews

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** RESUME_STATE_CE_DEV2_20260623_BUILD-MANDATE-N2.md (Wave 1 = DONE). **READ THIS + MEMORY.md FIRST.** origin/main @ `f31b589a`.

## 🔝 TOP PRIORITY (Operator-flagged 2026-06-23)
**forge.re_review (ce-ops#151 / PR #337) — wire in CE's DIFF-AWARE re-review lane.** It's the mitigation for a governance-posture change I made today (see Bot-fix). It classifies a PR head-change as base-only-rebase (approval stands / fast re-approve via `git range-diff`) vs scoped-content-change vs full. **A worker in THIS session is finishing #337** (branch `ce151-stale-review-reconcile`: address its CHANGES_REQUESTED, rebase, fix CI, re-green) + returning a WIRING-GAP assessment (what's left to make it gate re-reviews in the live dispatch flow — Phase 2). On worker report: route re-review → land #337 → scope+build the wiring (~1 agent-day; overlaps the Integrator). Est to operating: ~1.5–2.5 agent-days.

## ✅ WAVE 1 DONE — M2 visibility gateway + onboarding foundation (all merged)
#369 (#209 queue-deflake) · #364 (A2 channel-emission webhook sink) · #365 (PR-3 profile-PATH) · #366 (PR-2 install.sh robustness) · #367 (PR-1 verify-install, hardened trust anchor) · #368 (A1 PTY attachable-session substrate). Every PR independently reviewed, real findings caught+fixed. main @ f31b589a.

## 🔴 LIVE PR BOARD — route reviews (controller holds gate; merge on APPROVED+green via queue `gh pr merge <n> --auto`)
- **#337** `ce151-stale-review-reconcile` — forge.re_review (TOP). Worker finishing in-session. After: re-review → land.
- **#372** `ce-forge-rebase-dismiss-fix` — **bot-fix CODE PR** (durable fix; flips ruleset default False). Work-class fixed→`tiny`, CI re-running. **GOVERNANCE-POSTURE change → careful review + Operator sign-off before merge** (App dismissal authority). Author ce-overwatch/cedev2 → route to a dev seat.
- **#373** `ce197-onboard-orchestrator` — onboarding PR-4+5 (my worker; +1429, epic). **DIRTY** (registry `_versions.py` conflict vs merged #368 → needs rebase). Route review + a rebase.
- **#371** `ce197-launcher-refuse` — PR-6 (#212 launcher refuse-before-spawn, dev-4). Needs review.
- **#370** `ce207-notify-reports` — A2 scope-2 report-fold (dev-1). Needs review.
- Parked (Track C): #362 (docs, rebase) · #351 (drain-Q, CHANGES_REQUESTED) · #349 (live-site docs-nav, **APPROVED but ⏸️ Operator visual-check** — do not merge w/o snapshot+visual review).
- **DISPATCH DISCIPLINE:** #373/#370/#371/#337 — intersect manifests before co-enqueuing; #373 & #337 both touch `_versions.py`+`test_version_boundary.py` (serialize). [[ce-merge-queue-offloads-mechanics]]

## 🤖 IN-FLIGHT WORKERS (agentIds die on /clear — track via branch/PR)
- #337 finishing → `ce151-stale-review-reconcile` (+ wiring-gap report).
- dev-4 → #371 (done, PR open). dev-1 → #370 (done, PR open). My PR-4+5 → #373 (done, PR open, DIRTY).

## 🟢 BOT-FIX (ce-forge-dev-2[bot] dismissing approvals on push) — DIAGNOSED + LIVE-PATCHED
Root cause = ruleset **`ce-reference-protection-floor` (id 17946690)** `dismiss_stale_reviews_on_push:true` overriding classic `dismiss_stale_reviews=false` (blunt/non-diff-aware, fired on rebases). **LIVE PATCH APPLIED (Operator-blessed):** PUT ruleset → `false` (other protections intact: 1-approval, last-push-approval, thread-res, squash). Approvals now survive rebases. **#372** = durable source fix. **Trade-off blessed:** content-change re-review relies on diligence until forge.re_review (#337) lands → why #337 is TOP. [[ce-dismiss-is-not-approve]]

## 🏗️ NEXT PROGRAM (teed up, Operator-approved sequencing)
**Integrator MVP** (autonomous merge-mechanics) → `.ce/state/research/BUILD_MANDATE_INTEGRATOR_MVP_20260623.md` + design `DESIGN_INTEGRATOR_merge_mechanics_20260623.md` + **ce-ops#216**. 5 units (eviction-detection → deterministic resolver library [today's hand-resolved conflicts are the spec] → executor+race-guard → escalation seam). **PREREQUISITE = bot-fix/#372 + forge.re_review.** [[ce-integrator-merge-mechanics-agent]]
**SEQUENCE:** finish onboarding wave (#370/#371/#373 + PR-7 install.sh hybrid still TODO) + land #372 + **#337 (TOP)** → **Integrator MVP** → **belt-arming** (one-seat canary `pickup poll --claim --enable-launch` → fleet; belt is currently OBSERVE-ONLY: crons run bare `pickup poll`, NOT armed; dev-4 has no belt cron). Arming AFTER Integrator (else floods manual merge leg). [[ce-belt-feed-polling-default-push-premium]]

## 🆕 TODAY'S DURABLE DECISIONS (memories written/updated)
[[ce-design-artifacts-in-ceops]] (DESIGN_*/mandates → private ce-ops via fixed sync-ops.sh; ce-ops#215 = seat read access) · [[ce-pr-work-class-line-format]] (bare SIZE token tiny/story/feature/epic, no parenthetical, NOT v1/v3 — recurring CI trip; specify in every brief) · [[ce-merge-queue-offloads-mechanics]] · [[ce-dismiss-is-not-approve]] · [[ce-integrator-merge-mechanics-agent]] · [[ce-visibility-channel-emission-model]]+[[ce-agent-pointed-install-model]] (Wave-1 design basis).

## 🖥️ MECHANICS / REACH
- dev-4 = `ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`) · dev-3 = `ssh dev3` (tmux `dev3-onboard:0.0`) · dev-1 = `ssh dev1` (tmux `ce-dev1-orchestrator:controller`). Codex gpt-5.5 high, clean ce 0.2.0. Seat dispatch = `cat brief | ssh <h> "tmux load-buffer -b X -; tmux paste-buffer -p -b X -t <pane>; sleep 0.3; tmux send-keys -t <pane> Enter"`. **Brief seats SELF-CONTAINED** (design docs gitignored; seats lack ce-ops checkout until #215).
- Force-compact a stuck idle codex seat: `tmux send-keys -t <pane> -l '/compact'; sleep 0.4; tmux send-keys -t <pane> Enter`.
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Queue: `gh pr merge <n> --auto` (no --squash); verify enqueue via graphql mergeQueue (a 2nd `--auto` says "already queued"). reviewDecision==APPROVED + green required; **verify reviewDecision==APPROVED on CURRENT head** (not just block-cleared).
- ce-ops sync: `cd ~/ce-ops && ./sync-ops.sh "msg"` (CE50 pin advisory warning is pre-existing/non-fatal). Ruleset re-apply via `ce ... ruleset --apply` once #372 lands.
- ce-root-v1 key `~/.ce-keys/ce-root-v1`(+.pass); CF DNS `~/.ce-keys/cloudflare.env`.

## ⏸️ ESCALATION LINES
Governance-posture changes (#372 merge, Integrator autonomy bounds) → Operator bless · #349 live-site visual-check → Operator · M2-arch beyond #207/#208 (E-att container decisions) · version bump/publish · new live-work surface = redaction gate + secret-leak test.

## 📋 NEXT-SESSION FIRST ACTIONS
1. Check #337 finishing-worker report → route re-review → land (TOP). Read its wiring-gap assessment → scope Phase 2.
2. Route reviews for #370/#371/#372/#373 to non-author dev seats (conflict-disjoint; #373 needs a rebase first; #372 needs Operator sign-off pre-merge).
3. Confirm #372 CI green (work-class fixed); enqueue once approved + Operator-blessed.
4. After onboarding wave + #337 land → dispatch Integrator MVP per BUILD_MANDATE_INTEGRATOR_MVP. Belt-arming AFTER.
5. Dual-write this resume to CE-DEV-1 + ce-ops at first checkpoint.
