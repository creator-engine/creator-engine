# RESUME STATE — CE-DEV-2 — 2026-07-05 ~09:50Z (day-arc checkpoint #3, pre-/clear)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260705T1100Z.md (that file's name
> overstated the hour; THIS one at 0950Z is NEWEST by mtime — trust mtime). Arc SSOT =
> DAYARC_MANDATE_CE_DEV2_20260705.md (RATIFIED + execution log + 0.3.2 release checklist inside).

## ⏸️ AWAITING-OPERATOR (surface FIRST; asked + explained in-session, no answer yet)
1. ghcr visibility click: org packages → ce-runtime → settings → Danger Zone → Public. Blocks
   tenant docker pull. Repeat for ce-seat after its first publish.
2. chmod735-dor canary sandbox go-ahead: controller pre-creates ce-canary-sandbox via
   mythos-overwatch (~/.ce-keys/mythos-overwatch.pat; ce-overwatch has NO standing in that org),
   mythos-ce App installed on it (may need Operator click), full-DoD BROWNFIELD canary via App
   creds = Arad-fidelity Model-C. No PAT mint needed.
3. NOTE: Operator flagged the AskUserQuestion-chip ratification as too thin — plan was re-presented
   in-session; future mandates: show the full plan BEFORE any ratification form.

## MERGE STATE (exact @09:49Z): merged today ≤ #808 incl. (#795-#805, #808). OPEN, ALL APPROVED,
## chain walking: #806 npm-fix · #807 runbook-gaps · #809 s1a docker backend (CRITICAL: its merge
## fires dev-4 s1c poll) · #810 docs-accuracy · #811 compliance tiny · #812 didyoumean guard.
## Every PR #802-#812 got independent Sonnet review + evidence-backed approval as ce-dev-2;
## amendment rounds ran PRE-approval (no marker churn). #803 needed the stale-marker repair once.

## BOARD
- dev-1 (tmux, DOUBLE-Enter): cleared, then BATCH = ce-401-doctrine-coverage-fastfollow +
  ce-403-scanner-hardening-fastfollow (parallel workers; brief /var/tmp/BRIEF_ce401_403_hardening_batch.md).
  Has durable no-proactive-rebase guidance.
- dev-3 (ce-vps-codex via ssh dev1): idle-with-queue — ce-415-followup-tinies STARTS when #808
  title on origin/main (condition NOW TRUE — expect it to start/signal soon; brief embeds the
  schema-regen obligation).
- dev-4 (ce-dgx-codex local): polling for #809 title on origin/main → s1c
  (ce-s1c-launch-default-policy, brief on seat, fail-closed D-i + seat-image-ref D-ii decisions
  embedded) → then ce-onboard-relaunch-ux (same launch_runtime.py, serialized).
- POOL (tinies from reviews): runner helper-dedup + private-import cleanup (post-#809) ·
  ce-session framing in pilot-runbook/macos pages · quickstart step-numbering ·
  #796 notes (no-skew test, override-msg order, env-var doc) · #797 --repo-scope-only ·
  #801 installer env-var enumeration · #804 text-parse coupling comment.

## EVENT → ACTION MAP
- #809 merge → dev-4 s1c starts by itself; #808 merged → dev-3 tinies start by itself. Seat
  READY signals → verify pane → harvest_intake (contained: bundle+exec-cat, host preflight
  arbiter — but remember s1a: blocks can be REAL [[ce-new-ce-group-docs-coupling]]) → PR →
  fetch+worktree+diff-file → Sonnet reviewer ("author=seat X, you are independent") → approve as
  ce-dev-2 on green (waiter pattern) → chain.
- s1c + relaunch-ux + dev-1 batch merged + Operator items → 0.3.2 RELEASE CEREMONY per mandate
  checklist: cut off current main · regen install.sh embedded profile-block heredoc (hand-dup'd
  broken npm block!) · llms-install.md:239 onboard→install · wheel unzip-grep verify · controller
  signs ce-root-v1 INLINE (never a worker) · publish downloads/0.3.2 + mirror · seat-image ghcr
  publish + visibility click · RE-RUN canary A (fresh ce-canary-a on VPS) + canary B
  (/var/tmp/ce-canary-b DGX) against LIVE artifacts → DoD evidence → Arad handoff pack.
- C5 cutover retry: ALL code gates DONE (#793/#794/#799/#800/#805) — needs quiet window
  (tonight); one-command block in A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md §C5; local image
  rebuilt from da89bf2f (gh 2.96.0 SMOKE-OK) — REBUILD AGAIN from post-#805 main before retry;
  ghcr ce-runtime@0.3.1 digest sha256:7618dbe8811d467c71ae2a8fec231e38fc837532a1dd09b7fe4e7f0dd575353c.

## HYGIENE (next session, after merges): prune claims + review worktrees for merged PRs
## (wt-ce803..812-review, wt-ces1a-harvest, wt-ce415-harvest, wt-cec5prep-harvest, wt-ceguard-harvest,
## wt-cecompl-harvest, wt-ce434-harvest2) — `git worktree remove --force` each; plus the ~123
## legacy stale worktrees (N-E backlog). Canary envs preserved deliberately (ce-canary-a VPS,
## /var/tmp/ce-canary-b DGX). Wall daemon healthy but logs to a PRIOR session's /tmp scratchpad
## (rollback-launch.log) — move log path at next daemon restart.

## WATCHERS (MINE, persist): b786f65ro PR-board · bw2w5n0yz seat-signals (tightened: last-40-lines
## + full signal shape) · bmosax1vr daemon-log errors. NO waiters outstanding (all consumed).
## Prior-session watchers all dead/stopped — do NOT resurrect; check TaskList before spawning.

## TICKETS today: #447 S1 (units A merged-ish/B merged/C pending) · #448 npm (wheel side ~done via
## #806; install.sh side BOUND to 0.3.2) · #449 docs (closed by #810 when merged — VERIFY then
## close manually, cross-repo Closes is a no-op) · #450 onboard-UX (relaunch-ux unit pending) ·
## #451 surfaces-checker · #388 wiring COMPLETE comment posted · #435 closed · #384 role-gap
## evidence. Close #417/#414 tickets after their PRs' merges confirmed (manual close).
