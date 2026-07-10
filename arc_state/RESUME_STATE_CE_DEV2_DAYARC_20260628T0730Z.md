# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~07:30Z — RELEASE MERGING + 4 WAVES LANDED

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0615Z/0520Z. Dispatch MECHANICS detail = 0520Z (proven, unchanged).
> ⭐ STANDING ROLE: OVERARCHING ORCHESTRATOR — drive via codex controllers (dev-1/3/4), NEVER inline build work. [[ce-dev2-orchestrator-role]].

## AUTH (see MEMORY.md header)
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge (queue sets strategy): `gh pr merge <n> --auto --merge`. ce-root-v1 key/pass/pub = ~/.ce-keys/ce-root-v1{,.pass,.pub}.

## OPERATOR LANE: engine fan-out W1-W9; onboarding (W10) HELD. 0.3.0 sign+publish AUTHORIZED to me; #592 arm AUTHORIZED (done).

## 🔴 IMMEDIATE ON RESUME
**TAG THE 0.3.0 RELEASE when #603 merges.** #603 (branch release/0.3.0-publish, head 4d12d80d) = the signed 0.3.0 publish (docs/llms-install.md SSHSIG + docs/downloads/0.3.0 mirror + version-pinned test/source fixes + carriers). State at checkpoint: APPROVED (ce-dev-2) + auto-merge armed + CI "Validate governance artifacts" pending → merges on green. **On merge: `git fetch origin && git tag -a release/v0.3.0 <merge-sha> -m "CE 0.3.0" && git -c credential.helper='!gh auth git-credential' push origin release/v0.3.0`** (mirror the release/v0.2.0 tag precedent). Then 0.3.0 is LIVE → report to Operator. If #603 went RED again: it failed gates serially before (version-pinned tests→work-sizing floor→path-manifest carrier); run FULL `ce validate-pr` once, fix ALL, re-approve on new head (a push dismisses approval).

## ✅ MERGED THIS SESSION (engine waves)
- **#592 W4a/W4b** — AutoReview self-trigger, never-APPROVE 3-layer enforced; **AutoReview is ARMED fleet-wide** (AGENTS.md trigger live). ⇒ W5/#295 UNBLOCKED.
- **#604** — SSOT: mandate full `ce validate-pr` before EVERY push incl releases (Operator directive).
- **#605 W2** — Autonomous Release Phase A (release-bump/changelog/orchestrator/release.yml) in cli.py.
- **#606 W3** — evidence-bundle press-merge surface (has_authority:false; reuses fanin_runtime).

## SEATS (at checkpoint)
- **dev-3**: Working **W1a** (ce-ops#291 CEO-mode classifier, branch ce-291-automerge-classifier-dryrun; brief .ce/briefs/brief-ce291-w1a-automerge-classifier-dryrun.md), ~77% ctx. → on land: harvest+review(Sonnet)+gate; then dev-3 → **W6a ce push** (dev-3 has the LIVE broker).
- **dev-1**: IDLE, compacted (~0% ctx), ready. → **W8** (forge triage #187 + #42 `ce dispatch plan`; ce_cli.py is FREE since release went to cli.py). Needs a file+pointer brief (read #187 design first).
- **dev-4**: IDLE, clean box. → **W5/#295** (annoyance→tool + agents author own AGENTS.md; inputs = filed tickets #340/#341/#342) OR another lane. (dev-4 flaky earlier: conveyor-tend compacted it mid-W3; W3 was moved to a host worker → #606 merged.)

## QUEUED LANES (batch-dispatch when release lands / dev-3 frees — token-lean, don't over-spawn)
W5/#295 (→dev-4 or dev-1) · W8 (→dev-1, brief from #187/#42) · W6a ce push (→dev-3 after W1a) · W9a/c brain (→ MY OWN host implementer — needs host-local MEMORY.md/corpus; W9b hydrate = a seat) · W2f parity-in-validate.yml (⚙️) · W2e release/* tag ruleset (🔒, only for AUTOMATED release path) · W6b/W6d dev-4 push+self-review brokers (🔒).

## HARD-WON DISCIPLINE (do NOT regress — all cost CI round-trips this session)
1. **FULL `ce validate-pr` in ONE pass before pushing ANY PR** (incl releases/controller-authored). Two-strikes: never reactive whack-a-mole. It catches: `verify-work-sizing-floor` (declared class MUST satisfy diff floor — large/release diffs → epic; validate.yml:415), **path-manifest carrier** (G-ii: `.ce/pr-manifests/<slug>.md` path-set == base..HEAD diff — regenerate via `carrier_gen.write_carriers(base=<merge-base-sha>)` Python API, NOT hand-edit; CLI dirty-checks on stray `validators/build/` artifacts so use the API + rm build/egg-info first), changelog carrier. [[ce-run-full-preflight-before-push]] pts 9/10.
2. **G5 PR-body line** `- **Declared work class:** <tier>` (floor-satisfying) — FORGE-ONLY gate (reads pull_request.body); local suite can't see it. ce-ops#340 auto-emit. **A new push dismisses approval → re-approve on new head.** Body-only edit doesn't re-trigger CI (`edited` not in triggers; rerun replays stale body) → **close+reopen** (ce-ops#342).
3. **ALL seat injections (initial + re-briefs/corrections) = file+pointer+SHA**, never inline paste (caused an unsubmitted 1018-char blob in dev-4). Transfer via `cat brief | <docker exec -i> tee /tmp/X.md` (stdin, not argv). herdr: submit=`send-keys Enter`; clear stuck box=`send-keys Escape`/`ctrl+u` (format `ctrl+X`, NOT `C-u`). [[ce-seat-dispatch-prompt-pointer-sha]].
4. **Every subagent spawn sets `model` explicitly** — Haiku=mechanical (ops_triage, liveness recon, verification), Sonnet=substantive (architect_research, implementer, harvest_intake, reviewer), Opus=CONTROLLER ONLY. Omitting it inherits Opus = violation. [[ce-model-effort-routing-policy]].
5. **Host /tmp/.git trap**: raw pytest false-fails ~70 fanin/transcript/PacketRootNotIgnored tests (stray /tmp/.git owned by cedev4); `ce validate-pr` sets TMPDIR=/var/tmp = hermetic. Tell every host worker to use ce validate-pr, not raw pytest.

## RELEASE CEREMONY (for the NEXT cut — proven this session)
Stage from a clean origin/main worktree at the version commit: `PYTHONPATH=validators /home/cedev2/creator-engine/.venv/bin/python -m creator_engine_validator.cli release-stage --repo-root <wt> --version X.Y.Z --out <out> --sign-mode placeholder --signing-key-id ce-root-v1` (.venv python has `build`). Sign: `SSH_ASKPASS=<cat ce-root-v1.pass> SSH_ASKPASS_REQUIRE=force setsid -w ssh-keygen -Y sign -f ~/.ce-keys/ce-root-v1 -I ce-root-v1 -n ce-spec-v1 - < llms-install.canonical > llms-install.md.sig`; substitute `base64 -w0` sig into the `value:` line; verify via `release_publish._canonical_install_spec` → sha == signed canonical + `ssh-keygen -Y verify`. Publish = commit docs/llms-install.md + docs/downloads/X.Y.Z (NOT the canonical/sig/manifest staging files). **Version-pinned refs that MUST bump X-1→X**: test_v3_installer.py, test_install_bootstrap.py, test_onboard_apply_live.py, and SOURCE `onboard_apply_live.py` uv mirror URL (release-integrity). Durable fix = make those tests version-agnostic (ce-ops#343). SIGNING stays on-host (root key never leaves) — the one non-delegable act; everything else → Sonnet workers.

## WATCHERS/CRONS/LOOP
- Harvest-monitor **/loop ARMED** (ScheduleWakeup ~07:29Z) — SURVIVES /clear (OS-level); on fire it re-enters /loop with a full-context prompt (tag release, batch W5/W8/W6a, harvest dev-3 W1a). Plus PR-board Monitor (persistent, pings new PRs), hourly controller cron, conveyor-tend (:30, compacts IDLE seats >40% — causes apparent "stuck"; filesystem/worktree survives), poll-devs (:05), seat-check (:00).
- **OpenBao wall token: renew before 15:42Z** (G4) — ~8h buffer at checkpoint.

## MISC
- tldr output style created at `~/.claude/output-styles/tldr.md` (THIS session = direct claude, NOT ce-launched; for ce-launched seats use project `.claude/output-styles/`). CE install does NOT touch ~/.claude; `--setting-sources project` excludes user settings; spec-kit skills are project-scoped (repo .claude/skills/), not installed to ~/.claude.
- Filed tickets: #339 (dev-4 libsodium), #340 (G5 auto-emit), #341 (strangeLoop run_mode), #342 (empty-commit→CI), #343 (version-agnostic install-spec tests).

## ORCHESTRATION LEARNINGS (→ brain W9)
- Built #603 release WITHOUT a full preflight (only signature) → 3 serial CI gate failures (test-pins/floor/carrier). Lesson: controller-authored PRs get the SAME full ce validate-pr as seats, upfront, in one pass.
- Brief-distillation via architect_research (Sonnet) keeps controller context lean + drop-in self-contained briefs.
- Workers stall on host /tmp/.git unless told to use ce validate-pr; grep-of-worker-output can MISREAD mid-process errors as "stuck" — wait for completion before concluding.
- nudge-don't-restart (SendMessage) preserves a worker's committed work.
- conveyor-tend compacting idle seats mid-lane looks like "stuck"; verify the worktree (survives compaction) before re-dispatching.
