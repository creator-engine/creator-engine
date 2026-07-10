# RESUME STATE — CE-DEV-2 — 2026-07-04 ~18:40Z (NIGHT-ARC start checkpoint; Operator departed)

> MEMORY.md first. Arc SSOT: NIGHTARC_MANDATE_CE_DEV2_20260704_EVENING.md (RATIFIED ~18:30Z,
> full ambition incl. C5 gated cutover). Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260704T1700Z.md.

## ⏸️ AWAITING-OPERATOR (surface FIRST)
**CE410_REARMING_BUNDLE_20260704.md is READY** (assembled ~20:45Z; form-echo decision text inside;
13/13 evidence verified, 7/7 gate-adjacent reviews substantive, honest provenance caveat on the
verification base SHA). NO arming, NO registry publish, NO external release tonight (reserved).
N-A COMPLETE: #787 (s3b) + #788 (s10) MERGED 18:37/18:38Z — CE-410 code-complete, all 10 slices on
main. Seats re-stocked: dev-1=s3c (brief sha 4cdc8fa1…) · dev-4=G8 Dockerfile fix (sha e39dcb8e…) ·
dev-3=still fast-follows. Claims recorded for both new units.

## RATIFIED TODAY (evening session)
- **A2-SEQ Option A** (memo .ce/state/research/A2_DOUBLE_DRIVE_SEQUENCING_DECISION_20260704.md,
  memory ce-a2seq-singleton-cutover-ratified): merge-gate singleton; containerized replaces host
  via cutover; kill-switch = ~/ce-wall-daemon-launch.sh; review-pickup decoupled.
- **Night-arc mandate** (full ambition). Cutover C5 = pre-authorized but HARD-GATED (all preflight
  green + zero in-flight PRs + quiet window ≥2h + kill-switch verified; anomaly → rollback + halt).

## MERGED THIS SESSION: #782 #783 #784(CE-410 s9) #785(s3a) #786(A1 shadow daemon). Chain zero-touch post-approval, 5/5.

## TICKETS FILED TODAY: ce-ops#442 (ce-root-v1 custody; INCIDENT: harvest worker self-signed
llms-install.md on #785 — see memory ce-worker-must-not-sign-ce-root-v1; STOP-line now mandatory
in signed-artifact briefs) · #443 (A1 fast-follows, being implemented by dev-3) · #444 (queue-daemon
startup lease = N-C C3) · #445 (cutover gaps G1-G7 = N-C C1/C2; fact base
A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md).

## BOARD (all dispatched with pointer+SHA, Working-verified)
- **dev-1** (tmux ce-dev1-orchestrator:2.0; needs SECOND Enter on sends): ce-440-s3b systemd
  ExecStart cev3→ce. Brief /var/tmp/BRIEF_ce440_s3b_systemd_exec_migration.md sha=f875d996….
  Self-pushes PR. Signal READY-FOR-HARVEST ce-440-s3b-systemd-exec-migration <sha> PR #<n>.
- **dev-3** (ce-vps-codex via ssh dev1; herdr IN-CONTAINER: `ssh dev1 'sudo docker exec -e
  HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr …'`): ce-388-fastfollow-lease-ux
  (#443: lease-error handler+test, --dry-run→--one-shot, RUNBOOK.md). Brief
  /var/tmp/BRIEF_ce388_fastfollow_lease_ux.md sha=9e83420d…. Contained → harvest on signal.
- **dev-4** (ce-dgx-codex local; herdr in-container, same env pattern, second Enter): ce-410-s10
  publish-reverify-audit (LAST slice before Re-Arming Bundle). Brief
  /var/tmp/BRIEF_ce410_s10_publish_reverify_audit.md sha=da142a00…. Contained → harvest on signal.
  Gate-adjacent → independent review mandatory.
- **Worker (background)**: C1 image build — `creator-engine/ce-validator:0.3.1` native aarch64 from
  #781 scaffolding, local only. Verify arch=arm64 + smoke. May report a #377-class amd64 digest-pin
  blocker → that becomes a seat PR (#445).

## EVENT → ACTION MAP (night)
- Any seat PR/signal → harvest (contained: bundle-stream; dev-4 via exec-cat NOT docker cp) →
  fetch+worktree → reviewer w/ embedded main-side facts → approve as ce-dev-2 on green → daemon
  chain merges → prune → RE-STOCK the seat from N-C/N-D/N-F.
- s10 merges → assemble Re-Arming Bundle (design SSOT CE410_ARMING_FIX_DESIGN "Re-Arming Evidence
  Bundle Required": code/test/review evidence, slices 2,6,8,9,10) → ⏸️ marker.
- s3b merges → dispatch ce-440-s3c (tiny, 3 lines INSTALLED_CE_DOGFOOD_MIGRATION.md:42,47,66) to any seat.
- fast-follow merges → C3 (#444 lease; v3_cli.py territory — FREE, verify at dispatch) and/or C2
  (#445 plumbing: run-daemon-container.sh env/cacert/tmpfs — verify vs any in-flight) to freed seats.
- ALSO queued for next free seat: **G8 Dockerfile fix** (#445 comment 2026-07-04): offline
  setuptools via wheelhouse-dev COPY in deploy/runtime-image/Dockerfile + deploy/oci/Dockerfile
  (tiny/story; C1 built the image via workaround — repo fix makes clean-pull + #781 publish workflow buildable).
- C1 ✅ DONE: ce-validator:0.3.1 local, arm64, smoke green (sha256:66fedb4e…). G1/G7 closed; G8 opened.
- C1 done + C2/C3 merged → C4 preflight dry-run → C5 ONLY if all gates true, else stage + note.
- N-D design ✅ DONE: SSOT = ND_REVIEW_PICKUP_OPENBAO_WIRING_DESIGN_20260704.md (machinery generic;
  D1 story = supplier+flags+loop-refresh; D2 story = unit+env-docs+tests). ⚠️ SEQUENCING: D1 touches
  v3_cli.py = COLLIDES with C3/#444 (also v3_cli.py) → dispatch C3 first (next freed seat), D1 only
  after C3 merges; D2 after D1. Operator deployment prereqs (vault PAT, BAO token, policy-sha doc,
  ALLOWED_REFS) = morning ⏸️ queue — code merges don't need them.
- N-E: rc2-anomaly disposition (dirty codex-bump files, ce-ops#377) — deliberate dispatch-or-archive;
  #442 PreToolUse quick-win if config-only.

## WATCHERS: b7hq6ib7g PR-board · b8gyypzb7 seat-signals (re-fires stale already-harvested signals —
check claims/PRs before acting) · bk46xs0g8 wall-daemon log. All auto-resume post-/clear; TaskList
may look empty for minutes — never re-spawn without checking.

## MECHANICS
- herdr = IN-CONTAINER binary (not host PATH); always -e HERDR_SOCKET_PATH=…; second Enter; verify
  Working/Context.
- Daemon chain: approval → settle → mint → enqueue → merge ~15-25 min; "governance_check_not_success"
  right after push = propagation lag, verify gh pr checks before worrying.
- Claims live: ce-440-s3b · ce-388-fastfollow-lease-ux · ce-410-s10 (+ files in .ce/claims/).
- Worktrees live: .ce/wt-ce388-shadow (KEEP) · .ce/wt-c1-imagebuild (worker-owned, self-cleans).
- Stale anomaly: main checkout on ce-release-0.3.1-rc2 + dirty codex-bump files = N-E disposition item.
