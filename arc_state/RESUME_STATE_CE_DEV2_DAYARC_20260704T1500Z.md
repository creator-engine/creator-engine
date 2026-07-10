# RESUME STATE — CE-DEV-2 — 2026-07-04 ~15:00Z (day-arc checkpoint #2, pre-/clear)
> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260704T1145Z.md.
> **Arc SSOT: DAYARC_MANDATE_CE_DEV2_20260704.md** (Arad/Nitzan PARKED below core lanes this arc
> + next night-arc).

## ⏸️ AWAITING-OPERATOR
**Nothing blocking.** Next Operator gate = CE-410 Re-Arming Evidence Bundle (after 8c/9/10).

## MERGED THIS BEAT (since 1145Z checkpoint)
#770 N5 worktree-prune (acceptance dry-run DONE: 670 scanned / 7 PRUNABLE / all risky refused —
evidence: .ce/state/research/N5_PRUNE_ACCEPTANCE_DRYRUN_20260704.txt) · #773 8a shared launcher
(leak-fix rework re-reviewed APPROVE, delta-verified by controller, merged) · #775 conveyor
discovery runner (approved on rework head b2aea00c, 3×green in merge group at checkpoint —
verify merged). Review loops: 2 more real catches (#774 regex false-negative, #775 missing
REWORK-suffix evidence) — 6 total this arc.

## BOARD (all seats Working at checkpoint; /clear dev-3+dev-4 before NEW dispatch — standing)
- **dev-1** (tmux ce-dev1-orchestrator:2.0): BATCH = #775 REWORK-test (DONE, b2aea00c pushed+
  approved) + **CE-410 8b sandbox runner** (brief sha a0352065, design SSOT co-transferred to
  /var/tmp; precondition #773-merged SATISFIED). Claim: ce-410-s8b-sandbox-runner.
- **dev-3** (ce-vps-codex): **#774 rework** (brief sha 8c0ce2e6 at /var/tmp/BRIEF_ce437s2_rework_774.md;
  fixes = widen SUBPROCESS_COMMAND_RE for sudo/abs-path systemctl + fail-closed manifest tests;
  branch OFF LIVE PR HEAD 6c973b38, extend-baseline-don't-weaken rule embedded). Expect signal
  `READY-FOR-HARVEST ce-437-portability-guard <40hex> REWORK`.
- **dev-4** (ce-dgx-codex): **#437 S3** containerize daemons + singleton-lease gate (brief sha
  dc6385a2 at /var/tmp/BRIEF_ce437_s3_containerize_daemons.md; claim ce-437-s3-containerize-daemons;
  stop line forbids launcher/discovery/CLI files).
- **Background worker LIVE at checkpoint**: ce-440 S1 FIX-FORWARD harvest worker on staging
  worktree .ce/wt-ce440s1-harvest (HEAD f219f85d) — fixing greenfield test onboard→install +
  minting brain-pin supersede (-v3 for brain-assertion-d1b-09-ce-cli-doc-coupling-v2), then FULL
  preflight → push → **opens the ce-440 PR itself**. ⚠️ It auto-resumes post-/clear and its PR-open
  will fire the PR watcher — do NOT re-dispatch; check for its PR/output first (gotcha hit AGAIN
  this session: prior-session ce-437 harvest worker auto-resumed → PR #774 while my duplicate ran;
  duplicate stopped pre-push, no damage).

## OPEN PRs AT CHECKPOINT
#774 portability guard: CHANGES_REQUESTED (2 blocking findings in review record), rework in
flight at dev-3. Rework-harvest rule: cherry-pick ONLY new seat commits onto live head 6c973b38.
#772 walkthrough: HELD until #440 S1 merges. (#775 merging; ce-440 PR opens when fix-forward done.)

## EVENT → ACTION MAP (what I do when each fires)
- ce-440 PR opens → review leg (fetch+worktree first; Sonnet; if hardening vocab → Haiku reframe).
- dev-3 REWORK signal (real 40-hex) → rework harvest onto #774 live head; then re-review delta;
  then approve if fixed; dev-3 next task = queue.
- 8b PR opens → review leg (authority-bearing: receipt minting/HMAC/tree_sha binding focus).
- dev-4 S3 signal → harvest (runsc bundle-stream mechanics; docker exec cat, ..HEAD range).
- #775 merge close → lane A next leg: disarmed shadow daemon run reading real seats (design
  intent in ce-388 lineage; discovery runner now on main).

## DISPATCH QUEUE (after in-flight)
① 8c wire conveyor armed-mode validate-runner to 8b (after 8b merges) ② belt shadow-arming A2
(two systemd units dev1 host; DevOps-shaped, controller MAY run inline-as-DevOps) ③ automerge
tier extension A3 (full ratified docs-class envelope) ④ #772 rework (post-#440-S1 merge)
⑤ dev-4 post-S3 = next hardest (9/10 chain or conveyor shadow) ⑥ N5 --apply sweep (optional,
after Operator sees dry-run evidence).

## WATCHERS (live; ALL may auto-resume late post-/clear — DEDUPE ON SIGHT, never re-arm blindly)
b1ltmk3fi seat-signals dev-1/3/4 · biofk6atk PR head/review/checks · b3ugle6qd PR opens/closes ·
bb0uytayt wall-daemon log (delivers stale lines late — trust gh pr view mergedAt over event order).

## MECHANICS GOTCHAS (new this beat — additive to 1145Z list)
- **herdr lives INSIDE the containers** (/usr/local/bin/herdr in BOTH ce-vps-codex and
  ce-dgx-codex; sockets /run/creator-engine/herdr/ inside container; host has NO herdr). Drive:
  `[ssh dev1] sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock <ctr>
  herdr agent send w1:p1 "..."` then `herdr pane send-keys w1:p1 Enter`.
- Double-Enter needed on BOTH dev-1 tmux AND herdr seats (dev-1 8b dispatch sat in input box).
- `git bundle create` refuses bare-SHA positive endpoint ("empty bundle") — use `<base>..HEAD`.
- Stale installed validator pkg shadows worktree source → run preflight with PYTHONPATH=validators
  + CE_VALIDATOR_PYTHON=.venv/bin/python (durable-fix candidate; consider ops_triage ticket).
- **.ce/brain/assertions.yaml (TRACKED) pin drift = REAL CI failure** needing doctrine supersede
  mint (-vN+1, never mutate-in-place; .ce/briefs/ce407-evidence-pin-doctrine-RATIFIED.md) —
  distinct from the gitignored .ce/state/brain/ LOCAL false-RED gotcha.
- Known host baseline failure (not counted, baseline=1): test_install_bootstrap uv x86_64 URL on
  aarch64 DGX.
- Sonnet reviewer cyber-trip hit AGAIN (#775 — "hostile/injection" vocab in MY prompt); Haiku +
  parsing-robustness framing cleared it. Keep security vocab out of reviewer prompts.
- False-positive seat signals ×2 more (brief-echo with literal placeholder + diff + line-number);
  now ENCODED as rejection tests in the merged discovery runner.

## KEY FILES THIS BEAT
Briefs (durable copies in .ce/briefs/): BRIEF_ce437s2_rework_774.md · BRIEF_ce410_s8b_sandbox_runner.md
· BRIEF_ce437_s3_containerize_daemons.md. Claims: ce-437-s3-containerize-daemons ·
ce-410-s8b-sandbox-runner. Evidence: N5_PRUNE_ACCEPTANCE_DRYRUN_20260704.txt. Staging:
.ce/wt-ce440s1-harvest (fix-forward in progress). Review worktrees to prune when PRs close:
.ce/wt-774-review, .ce/wt-775-review, .ce/wt-773r2-review.
