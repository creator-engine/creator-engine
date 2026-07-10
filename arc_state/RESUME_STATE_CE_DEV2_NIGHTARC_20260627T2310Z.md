# RESUME STATE — CE-DEV-2 controller — 2026-06-27 ~23:10Z — NIGHT-SHIFT ARC (Operator OUT; harvest wave complete)

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 2025Z. (1747Z = drifted-fork, ignore.)
> ⭐ RECOMMENDATION: `/clear` before the NEXT wave — context is saturated; dispatch accuracy degrades at depth.

## IDENTITY / AUTH (see MEMORY.md header)
- CE-DEV-2 on DGX. overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto`. Issues=ce-ops; PRs=creator-engine.

## AUTHORITY (Operator signed out ~18:10Z)
- G1–G5 (DAYSHIFT_ARC_20260626_AUTHORITY_MANIFEST). G1 conveyor-merge = review-as-ce-dev-2 + enqueue if baseline-clean + carrier-pass + in-arc + work-class-declared + CI green; never red.
- **RESERVED — HALT ⏸️:** R2 = external release/publish AND fleet-wide arming (⚠️ **0.3.0 sign + #592 AutoReview arming are R2**). R1 fleet-rollout, R3 history-scrub, R4 weaken-guard, R5 irreversible, R6 new-scope.

## WORKER DISCIPLINE (proven tonight — KEEP)
- **NEVER `fork` for execution** (forks drift → one approved PRs as ce-dev-2 + armed merges unsupervised). USE restricted agents (`~/.claude/agents/`): `harvest_intake`, `fleet_recon`, `ops_triage` — all ran clean all night, zero drift. [[ce-no-forks-for-execution-use-restricted-agents]]
- **VERIFY before dispatch** (ticket-OPEN ≠ done; close-bot drift): grep code / check merged PRs FIRST. Mis-dispatched 3× early (#302→#567, #279→#558). Intersect file-territory vs in-flight PRs. [[ce-verify-not-already-landed-gotcha]]
- Context-gate before dispatch (>40% → /compact related / clear unrelated). Dispatch = brief→place(docker cp/scp + sha-verify)→herdr/tmux pointer+sha(base64). Contained-seat briefs SELF-CONTAINED.

## HARVEST WAVE RESULT (all dev work gated)
- ✅ MERGED: **#594** (ce-280 CI build-args, dev-1) · **#595** (ce-333 contributor docs, dev-3) · **#596** (ce-292 enforcement guard, dev-4) · **#598** (ce-338 curl-vector guard, dev-1).
- 🟢 LANDING (approved ce-dev-2 + auto-merge armed, on CI green): **#597** (ce-335 rename-aware gates — fixes the size-gate papercut) · **#599** (ce-326 onboard os-native default + doctor-test fix). CONFIRM both merge.
- ⏸️ HELD: **#592** (ce-292 AutoReview wiring — merging ARMS it fleet-wide = R2 Operator gesture; the guard #596 already landed) · **#593** (0.3.0 bump — CI-red on G5 body papercut; fix at cut-time; 0.3.0 sign = R2).

## ⚠️ SYSTEMIC PAPERCUT (fix next) — G5 "declared work class" line
The G5 gate requires the PR BODY to contain EXACTLY ONE line `- **Declared work class:** <tiny|story|feature|epic>` (a "Work class:" header or a `[PASS]` log line does NOT match). Hit **#593, #597, #598, #599**. I baked the exact-format requirement into the last harvest dispatch (harvest_intake auto-fixed #599). **TODO: persist it into `~/.claude/agents/harvest_intake.md` step 4 + the dev brief template** so it stops recurring. Consider a tooling ticket (carrier_gen/PR-template emits the line).

## FLEET — ALL IDLE (re-feed for next wave; VERIFY each first!)
- dev-1 (VPS tmux ce-dev1-orchestrator:2.0, self-pushes), dev-3 (contained f3526a6bca34, ssh dev1+docker, harvest its work), dev-4 (DGX ce-dgx-codex local docker, harvest; ⚠️ container **libsodium gap** fails check-examples → harvest-on-host re-validates).
- Re-feed candidates (RE-VERIFY undone + non-colliding before dispatch): #325 (B1 signing-anchor inverted), #334 (packaging test silently SKIPs), #327 (per-user GitHub App identity — see gap below), #295 (annoyance→tool + agent-AGENTS.md), #336 (wheel-bake test — ⚠️ a PR search matched, CHECK for existing PR first). NOT #335/#338/#280/#279 (done). 

## KNOWN GAPS / TICKETS
- ce-ops#337 (self-push intermittent, broker socket #285) · ce-ops#338 (curl-vector — DONE via #598) · #336 (wheel-bake flake). 
- **Contained-seat commit identity is generic** (`CE Worker`/`Codex`, not the real dev account) — no per-seat GitHub identity injection in the container. Relates to #327. Worth a ticket if not covered.
- dev-4 container libsodium gap blocks contained `check-examples` preflight (harvest-on-host sidesteps) — worth a ticket.

## NEXT ACTIONS
1. Confirm #597 + #599 merge (armed). 
2. Persist the G5-body-line fix into harvest_intake.md + brief template (stop the papercut).
3. Re-feed dev-1/dev-3/dev-4 — VERIFY each ticket undone + territory, context-gate, foreman reminder. (Ideally after a /clear.)
4. Crons/watchers armed (poll :05, conveyor-tend :30, belt 5m). **Renew OpenBao wall token before Jun 28 15:42 (G4).**
5. ⏸️ HALT for: 0.3.0 sign, #592 arming, R2 auto-merge flip, first belt run, any stop-condition.

## ON OPERATOR'S DESK (R-reserved)
0.3.0 sign (after #593 G5 body fix at cut-time) · #592 AutoReview arming · ce-dev-2 PAT mythos re-scope · R2 auto-merge flip + first belt run · Arad retry + Nitzan send.
