# RESUME STATE — CE-DEV-2 controller — 2026-06-27 ~20:25Z — NIGHT-SHIFT ARC (Operator OUT; driving autonomously)

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 1815Z. IGNORE the 1747Z file (drifted-fork, fabricated).

## IDENTITY / AUTH (see MEMORY.md header)
- CE-DEV-2 on DGX. overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge queue: `gh pr merge <n> --auto`. Issues=ce-ops; PRs=creator-engine.

## AUTHORITY (Operator signed out ~18:10Z)
- Grants **G1–G5** (DAYSHIFT_ARC_20260626_AUTHORITY_MANIFEST). G1 conveyor-merge = review-as-ce-dev-2 + enqueue if baseline-clean + carrier-pass + in-arc + work-class-declared + CI green; never merge red.
- **RESERVED — HALT to ⏸️:** R2 = external release/publish (⚠️ **0.3.0 SIGN+PUBLISH is R2 — staging OK, sign is Operator's**). R1 fleet-rollout, R3 history-scrub, R4 weaken-guard, R5 irreversible, R6 new-scope.

## DISPATCH/WORKER DISCIPLINE (hard-won tonight)
- **Use restricted custom agents, NOT `fork`** (forks drift — one approved PRs as ce-dev-2 + armed merges unsupervised). LIVE + working: `harvest_intake` (harvested #595 cleanly), `fleet_recon` (probed 3 seats), `ops_triage`. Set per-call model (sonnet for mechanical). [[ce-no-forks-for-execution-use-restricted-agents]]
- **VERIFY before dispatch:** a ticket's deliverable may already be on main (ticket-OPEN ≠ done; close-bot drift). Grep code / check merged PRs FIRST. Violated 3× tonight (#302→#567, #279→#558). Intersect file-territory vs in-flight PRs. [[ce-verify-not-already-landed-gotcha]] [[ce-dispatch-territory-map-before-dispatch]]
- **Context-gate before dispatch:** >40% used → /compact (related) or /clear (unrelated). [[ce-dispatch-context-hygiene-gate]]
- Dispatch mechanic: write brief → place in seat (docker cp / scp + sha-verify) → herdr/tmux pointer+sha (base64 through ssh layers). Contained seats brief must be SELF-CONTAINED (embed, no ce-ops refs they can't read).

## FLEET (20:25Z)
- **dev-1** (VPS tmux): IDLE. #594 done+enqueued. HOLD re-feed for **#335** (rename-aware gate fix — high value) until #594 MERGES (#335 touches validate.yml, would collide).
- **dev-3** (VPS contained f3526a6bca34): WORKING — fixing **#326** doctor-test regressions (its v3_installer.py change broke test_doctor_accepts_installed_console / _human_output_is_nonempty / _json_passes_on_governed_host; +3 NEW vs baseline). Branch ce-326-onboard-os-native-default (1 commit + fix).
- **dev-4** (DGX build seat ce-dgx-codex): its **#292-enforcement** (hook_check.py raw-API APPROVE block + test + reviewer.md, branch ce-292-autoreview-enforcement) is being HARVESTED by `harvest_intake` (agent ae2759aea) — dev-4's preflight RED was only the container **libsodium gap** (env, outside diff); harvest re-validates on host. Seat now idle.

## PRs / GATE
- **#595** (ce-333 docs) ✅ MERGED 19:37Z — first clean G1 merge (harvested from dev-3).
- **#594** (ce-280 CI build-args, dev-1) ✅ APPROVED + ENQUEUED (G1). Blockers self-resolved (brain-ledger dropped + OCI/RUST/DEBIAN entries landed on main). Queue rebases stale base + gates merge_group CI. CONFIRM it merges.
- **#592** (ce-292 AutoReview wiring) → RC (never-APPROVE was prompt-only). dev-4's enforcement PR (harvesting) adds the mechanical guard → then reconcile: enforcement lands → clear #592 RC / combine → merge.
- **#593** (0.3.0 bump) → PARKED, CI-red on G5 (PR body needs exactly one `- **Declared work class:** <tier>` line; drifted-fork malformed). Fix at cut-time; 0.3.0 sign = R2.

## KNOWN INFRA GAPS (tickets/notes)
- dev-4 container `ce-dgx-codex` lacks **libsodium** → check-examples/signature gate fails ALL contained preflight there. Harvest-on-host sidesteps; worth a ticket (blocks contained self-validate).
- ce-ops#337 self-push intermittent (broker socket staleness #285) — contained seats fall back to unauth push → harvest. Corrected evidence in #337.

## NEXT ACTIONS (autonomous)
1. Confirm #594 merges (queue) → then re-feed dev-1 #335.
2. harvest_intake (dev-4 #292-enforcement) reports → review → G1-merge → reconcile #592.
3. dev-3 #326 fix → harvest when READY → review → G1.
4. Re-feed seats as they idle (verified + non-colliding + context-gate + foreman reminder).
5. Watcher armed (bttvmeeqs: READY-FOR-HARVEST|did not push|preflight RED + new PR + 56m heartbeat). Crons: poll :05, conveyor-tend :30, belt 5m. Renew OpenBao wall token before Jun 28 15:42 (G4).
6. ⏸️ HALT for: 0.3.0 sign (R2), R2 auto-merge flip, first belt run, any stop-condition.
