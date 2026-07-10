# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~10:05Z — ✅ ce244 MERGED; RELAUNCH GREEN-LIT

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0906Z. Dispatch MECHANICS below.
> ⭐ STANDING ROLE: OVERARCHING ORCHESTRATOR — drive via seats/restricted workers, NEVER inline build work. [[ce-dev2-orchestrator-role]]. Each seat (me incl.) is born-a-foreman: drives multiple file-disjoint tickets; controller ensures parallel-safety via territory-map.

## AUTH (see MEMORY.md header)
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto` (NO strategy flag — queue sets it). ce-root-v1 = ~/.ce-keys/ce-root-v1{,.pass,.pub}.

## 🟢 RELAUNCH IS NOW GREEN-LIT (ce244 landed — the gate is cleared)
**#609 ce244 controller-bootstrap knowledge overlay MERGED at ~10:04Z → main mergeCommit ac8742e5.** This wired the deterministic controller-knowledge overlay (#244 bootstrap injection, slice 1). Relaunching dev-2 governed via `ce launch` is now PURE UPSIDE (restricts tools WITH the knowledge-load payoff active). **Relaunch sequence:** land ce244 (DONE) → checkpoint (THIS) → **Operator relaunches dev-2 governed (canonical `ce launch`, Opus/xhigh)** → fresh session resumes from THIS checkpoint WITH overlay-load active. End-state (later, M2 #207/#208) = CONTAINED governed controller; staged: governed first, contained second.
- ⚠️ RELAUNCH TIMING: a fresh `ce launch` session starts clean — THIS session's in-flight BACKGROUND WORKERS (the #610 correction implementer a4999394) do NOT survive; the relaunched session reconciles from this checkpoint + live PR board + seat panes and re-dispatches as needed. SEATS (dev-3/dev-4, separate processes) persist. Cleanest relaunch = next quiescent point (after #610 gates + dev-3/dev-4 harvests, ~15-30min) — but relaunch-now is SAFE (checkpoint captures all in-flight state). Operator's call.

## ✅ MERGED TODAY (28 Jun) — 8 PRs
0.3.0 LIVE — tag release/v0.3.0 → dcbc2d81. Merged: #604(SSOT preflight) · #605(W2 release-A) · #606(W3 bundle) · #592(W4a AutoReview ARMED) · #603(0.3.0 publish) · #607(W8 ce dispatch plan) · #608(W5 G5 body auto-emit) · **#609(ce244 bootstrap overlay slice 1 — RELAUNCH GATE CLEARED)**.

## 🎯 OPERATOR PRIORITIES (28 Jun — ENGINE-FIRST until onboarding)
Onboarding first test user + contributor = **~6h out, OPPORTUNISTIC** (onboarding capability already built+merged: ce onboard orchestrator #373, os-native default #599, welcome/getting-started #582/#589). Until then, top priorities IN ORDER:
1. **Forge/fleet automation** per Peter Steinberger research conclusions (.ce/state/research/PETER_STEINBERGER_AUTONOMY_ANALYSIS_20260627.md §5): lead track = throughput/amortization engine. Bets: #291 CEO-mode auto-merge (classify-only in flight = #610) · #341 AutoReview run_mode (in flight, dev-3) · forge triage · #295 agent-self-authored AGENTS.md (DEFERRED — was colliding w/ ce244; now ce244 LANDED so #295 unblocked) · #34 forge-side Overcut layer. (#218 belt-daemon already CLOSED.)
2. **Company brain** — UTMOST importance (ce-ops#79 AI-native persistent memory). → HOST implementer (needs host-local MEMORY/corpus, NOT a no-egress contained seat). Likely design-pass first — flag Operator for brain scope before build.
3. **Convert dev-1 & dev-4 to contained seats** — ONLY AFTER contained-parity verified (contained on par w/ non-contained). Needs a parity-verification lane first.
4. **Relaunch dev-2 governed** (above — gate now cleared).

## SEATS (live, 10:05Z)
- **dev-1** (VPS, NON-contained, tmux ce-dev1-orchestrator:2.0): FREE (ce244 self-pushed+merged). Self-push capable, no auto-notify (poll pane). → conveyor next forge/fleet lane (e.g. #295 now-unblocked, or #34 forge-side). Born-a-foreman.
- **dev-3** (contained ce-vps-codex VPS): WORKING **#341 AutoReview run_mode guard** — branch ce-341-autoreview-runmode from local main, 4-path tiny (tools/egress-broker/ce_egress_self_review_broker.py + validators/tests/unit/test_egress_self_review_broker.py + 2 carriers). Brief IN CONTAINER /workspace/creator-engine/.ce/briefs/brief-ce341-autoreview-runmode.md (sha 76c8d0ff). NO auto-notify (poll: `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'`). ⚠️ harvest-rebase will hit same-file #608 egress-broker changes (dev-3 base stale) — harvest_intake reconciles. → READY-FOR-HARVEST: harvest_intake(Sonnet) git-bundle extract→reviewer→gate.
- **dev-4** (contained ce-dgx-codex DGX-local): WORKING **#342 carrier-slug correction** (ce-342-ci-retrigger, validate.yml `edited` trigger; work done at 63c8fd4, only carrier FILENAMES needed dashed slug ce-342-). NO auto-notify (poll: `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1`). → READY-FOR-HARVEST: harvest_intake(Sonnet) git-bundle extract→reviewer→gate.

## 🔴 IN-FLIGHT GATE WORK
- **#610 (ce-ops#291 CEO-mode auto-merge classify-only, TOP BET)**: reviewer REQUEST_CHANGES (2 blocking, both mechanical; classify-only invariant CONFIRMED intact): **B1** dual pr-manifest collision (ce291a- orphan + ce-291- authoritative) → reconcile to ONE branch-slug carrier; **B2** validators/pyproject.toml package-data must add `forge/*.yaml` so automerge_mutation_policy.yaml ships in wheel (else classifier all-redaction in installed env; CI governance job doesn't test installed-wheel). CORRECTION implementer (Sonnet, a4999394, isolation worktree) fixing both on branch ce-291-automerge-classifier-dryrun + re-validate + push. → ON its report (new head): re-verify the 2 fixes + CI green → approve ce-dev-2 + `gh pr merge 610 --auto`. Re-create .ce/wt-ce610-review at new head if re-reviewing; clean after gating. (Head still 1951c2f8 at checkpoint — correction not yet pushed.)

## HARD-WON DISCIPLINE (do NOT regress)
1. FULL `ce validate-pr` GREEN in ONE pass before pushing ANY PR (declared-class+floor, path-manifest carrier via `carrier_gen.write_carriers(base=)` API, changelog, G5 body line `- **Declared work class:** <tier>`, + autogen `.ce/reference/cli.generated.md` via `python scripts/gen_cli_reference.py --write` for ANY new `ce` group — new-group coupling = 3-FILE set: README + test_v1_docs_reconciliation + cli.generated.md). Two-strikes, no whack-a-mole. baseline-diff = the regression authority. Host /tmp/.git trap → workers use ce validate-pr (TMPDIR=/var/tmp), not raw pytest.
2. G5 body line = FORGE-ONLY gate; body-edit alone won't re-trigger CI → close+reopen (ce-342 adds `edited` trigger to fix). A push dismisses approval → re-approve on new head.
3. ALL seat injections (briefs/re-briefs/corrections) = file+pointer+SHA; **contained-seat briefs must be COPIED INTO the container** (dev-3/VPS can't see DGX host .ce/briefs — `cat brief | ssh dev1 'sudo docker exec -i ce-vps-codex tee <path>'`). Control-signal confirms (go-push) ok inline. herdr: send=`herdr agent send w1:p1 "<ptr>"` + `herdr pane send-keys w1:p1 Enter`; read=`herdr pane read w1:p1`; verify landing via `Working` indicator (idle capture can be transient — re-read). tmux (dev-1) double-Enter past plan-mode hint.
4. Every subagent sets model: Haiku=mechanical (fleet_recon/ops_triage), Sonnet=substantive (architect_research/implementer/reviewer/harvest_intake), Opus=controller ONLY. ZERO fork, ZERO Opus subagents. EFFICIENCY: author dispatch briefs with a write-capable `implementer`(Sonnet) that writes the file directly (architect_research read-only → double-handling).
5. ⚠️ TERRITORY-MAP incl WORKTREES before dispatch (Haiku recon misses active worktrees).
6. HARVEST contained seats (dev-3/dev-4) via `git bundle` extract from container → host worktree → full validate-pr → push. dev-1 (non-contained) self-pushes (confirm-to-self-push). Controller holds the gate (review as ce-dev-2 + enqueue); seats NEVER approve/merge.
7. Gate = independent reviewer venue (author controller must NOT self-review the substance; dispatch a distinct reviewer worker). reviewDecision==APPROVED on CURRENT head before enqueue.

## LEARNINGS THIS SESSION (→ brain/#344)
- contained-seat brief must be copied INTO the container, not just host .ce/briefs (dev-3/VPS ≠ DGX host fs).
- harvest carrier-regen can leave an ORPHAN dual-manifest (ce291a- + ce-291-) — reconcile to single branch-slug carrier.
- wheel `package-data` must cover non-`.py` runtime assets (forge/*.yaml); the governance CI job does NOT test installed-wheel behavior → reviewer caught it, CI didn't.
- dev-4 container check-examples/well-formed-examples FAIL is environmental (missing libsodium, ce-ops#339) — non-blocking; main CI green arbitrates.

## WATCHERS / HOUSEKEEPING
- PR-board Monitor **boamzqs8y** persistent (merges/new-PRs/#609-#610 CI-failures). Loop heartbeat re-armed (~25min fallback).
- **OpenBao wall token: renew before 15:42Z** (G4).
- Onboarding(W10) opportunistic (~6h out). dev-4 git remote URL embeds overwatch PAT in plaintext (pane scrollback) — credential-in-URL leak surface; file/fix later.

## QUEUED LANES (conveyor as seats free)
dev-1 next: #295 (now-unblocked) / #34 forge-side / contained-parity-verification lane. · ce244 slice 2/3 (#344 prong 2 checklist content / prong 3 skill-ify ce-dispatch+ce-harvest) · W6a ce push · company brain (#79, host implementer, design-first). · W2e/W2f/W6b/W6d = 🔒 (release-tag ruleset / push+self-review brokers).
