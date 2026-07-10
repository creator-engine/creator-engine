# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~06:15Z — RELEASE IN FLIGHT + ENGINE FAN-OUT

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0520Z. Dispatch/harvest MECHANICS = see 0520Z checkpoint (unchanged, proven).
> ⭐ STANDING: I am the OVERARCHING ORCHESTRATOR — drive via codex controllers (dev-1/3/4), never inline build work. [[ce-dev2-orchestrator-role]].

## AUTH (see MEMORY.md header)
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge via queue: `gh pr merge <n> --auto --merge`.

## OPERATOR LANE: engine fan-out W1-W9; onboarding (W10) HELD. 0.3.0 sign+publish AUTHORIZED to me; #592 arm AUTHORIZED (arm-on-green).

## 🔴 CRITICAL NEXT ACTIONS
1. **0.3.0 RELEASE (#603)** — Operator-authorized sign+publish. SIGNED with ce-root-v1 (canonical `9fb30d53...`, SSHSIG ns ce-spec-v1, verified Good via tooling canonicalizer). Publish PR #603 (branch release/0.3.0-publish) = signed docs/llms-install.md + docs/downloads/0.3.0/ mirror + version-pinned test/source fixes. Declared class **epic** (floor needs it). Re-running CI after close+reopen → **auto-merge enqueued → merges on green**. ⚠️ **AFTER #603 MERGES: `git tag -a release/v0.3.0 <merge-sha>` + push** (mirror the release/v0.2.0 precedent). Signing key/pass = ~/.ce-keys/ce-root-v1{,.pass,.pub}.
2. **#592 W4a** — approved + auto-merge enqueued, declared class fixed → **arms AutoReview fleet-wide on green** → then **W5/#295 unblocks** (dispatch W5).

## MERGED THIS SESSION
- #604 (SSOT: mandate full `ce validate-pr` before EVERY push incl releases — Operator directive) · #605 (W2 autonomous-release Phase A: release-bump/changelog/orchestrator/release.yml in cli.py).

## SEATS
- **dev-3**: Working W1a (ce-ops#291 CEO-mode classifier, branch ce-291-automerge-classifier-dryrun, brief .ce/briefs/brief-ce291-w1a-automerge-classifier-dryrun.md). After W1a → W6a `ce push` (dev-3 has live broker).
- **dev-1**: IDLE, 75% ctx (just shipped #605). NEXT = W8 (forge triage #187 + #42 ce dispatch plan; ce_cli.py now FREE since release went to cli.py). MUST /compact first (>40%). Needs a W8 brief (read #187 design).
- **dev-4**: W3 STALLED — re-briefed twice, not progressing (likely flaky/compacted by conveyor-tend). Work INTACT in container worktree /tmp/w3-evidence-bundle-press-merge (commits 109d3f3, 3a88e39) on branch w3-evidence-bundle-press-merge. 3 gates to fix: schema-doc gen, product-lens PRESS_MERGE_BUNDLE.md (confidentiality), fanin_runtime import boundary. **PLAN: harvest to host + host implementer (Sonnet) fix** rather than keep re-briefing the flaky seat.

## QUEUED LANES
W8 (dev-1, after compact+brief) · W6a (dev-3, after W1a) · W9a/c brain (MY OWN host implementer — needs host-local MEMORY.md/corpus; W9b=seat) · W5 #295 (after #592 arms) · W2e release/* tag ruleset (🔒, only for automated release path) · W2f parity-in-validate.yml (⚙️).

## HARD-WON DISCIPLINE (don't regress)
- **PREFLIGHT = FULL `ce validate-pr` (not just pytest) before ANY push incl releases.** Includes `verify-work-sizing-floor --base origin/main --declared-work-class <wc>` (validate.yml:415) — declared class MUST satisfy the diff floor (large/release diffs → epic). #603 was red because I declared feature<epic floor; #592 red on PR-BODY format. [[ce-run-full-preflight-before-push]] pt 9/10.
- **G5 body line:** PR body MUST contain exactly one `- **Declared work class:** <tier>` (forge-only gate reads pull_request.body; local suite can't validate it). Harvest/release flows MUST set it. ce-ops#340 (auto-emit), #342 (close+reopen re-trigger — `edited` doesn't re-fire; rerun replays stale body).
- **ROUTING: every subagent spawn sets `model` explicitly** (Operator 2026-06-28) — Haiku=mechanical (ops_triage, liveness recon, verification), Sonnet=substantive (architect_research, implementer, harvest_intake, reviewer), Opus=CONTROLLER ONLY. Omitting `model` inherits Opus = violation. [[ce-model-effort-routing-policy]].
- **Host /tmp/.git trap:** raw pytest false-fails ~64-71 fanin/transcript tests (stray /tmp/.git owned by cedev4); `ce validate-pr` sets TMPDIR=/var/tmp internally = hermetic. Tell every host worker to use ce validate-pr, not raw pytest.

## WATCHERS/CRONS: PR-board Monitor (persistent, pings new PRs) · hourly controller cron (:47-ish) · poll-devs (:05) · conveyor-tend (:30, /compacts IDLE seats >40% — caused dev-3/dev-4 context resets) · seat-check (:00). Wall token renew before **15:42Z** (G4, ~9h buffer).

## ORCHESTRATION LEARNINGS (→ brain W9)
- Brief-distillation via architect_research keeps controller context lean + produces drop-in self-contained briefs.
- Workers stall on the host /tmp/.git preflight trap unless told to use `ce validate-pr`; nudge-don't-restart preserves their committed work (SendMessage).
- Release ceremony (sign) MUST stay on-host (root key never leaves) — the one reserved act not delegable; everything else (test-fix, source-fix, harvest, review) delegates to Sonnet workers.
- conveyor-tend compacting idle seats mid-lane causes apparent "stuck" — verify worktree (filesystem survives compaction) before concluding work lost.
