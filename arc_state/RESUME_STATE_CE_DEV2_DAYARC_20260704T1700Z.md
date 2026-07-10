# RESUME STATE — CE-DEV-2 — 2026-07-04 ~17:00Z (day-arc checkpoint #5)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260704T1600Z.md. Arc SSOT:
> DAYARC_MANDATE_CE_DEV2_20260704.md (containerized-first endgoal; ctx>45% definitive-/clear).

## ⏸️ AWAITING-OPERATOR
Nothing blocking. Upcoming gate: CE-410 Re-Arming Evidence Bundle (after A1 merge + slice 10).
Optional surfaces: ce-ops#441 bare-`ce` decision · ce-ops#442 (NEW: ce-root-v1 key-custody
enforcement — worker self-signed on #785 harvest, see incident below) · cyber-exemption form · N5 --apply.

## MERGED THIS SESSION: #782 #783 #784 (CE-410 slice 9 ON MAIN). #785 approved → in daemon chain.
All planned pruning done (wt-782/783/784-review, wt-s2-harvest, wt-780-review, agent worktree, s2 branch).

## OPEN PRs
- **#785** ce-440-s3a-docs-sweep (head 4fa25203, story, 22 files). APPROVED by ce-dev-2 ~16:55Z →
  daemon settle→mint→enqueue→merge. On merge: prune .ce/wt-s3a-harvest + local branch
  ce-440-s3a-docs-sweep; dev-3 goes idle (queue drained until A1 lands — see EVENT MAP).

## ⚠️ INCIDENT BANKED (this session): harvest worker self-signed llms-install.md with ce-root-v1
during #785 harvest (rename invalidated embedded SSHSIG). Artifact valid (ed25519 deterministic,
e2e green), ACT = non-delegable-signing breach. Memory: ce-worker-must-not-sign-ce-root-v1
(STOP-line now required in every brief touching signed artifacts). Product gap = ce-ops#442.

## BOARD
- **dev-1** (tmux ce-dev1-orchestrator:2.0, /cleared 16:20Z, Working): **ce-440-s3b** — migrate
  deploy/systemd/*.service ExecStart cev3→ce + test_gate_daemons_systemd.py:39 prefix. Brief
  /var/tmp/BRIEF_ce440_s3b_systemd_exec_migration.md sha=f875d996… (durable copy .ce/briefs/).
  Claim recorded. MANDATORY precondition in brief: ce queue-daemon/review-pickup --help must
  resolve via shim, else BLOCKED signal. Signal: READY-FOR-HARVEST ce-440-s3b-systemd-exec-migration <sha> PR #<n>.
  It self-pushes → controller reviews (fetch+worktree first; work class tiny).
- **dev-3** (ce-vps-codex): S3a HARVESTED (#785). IDLE after merge — do NOT re-dispatch S3a.
  Next work gated: slice 10 + #437-slice-3 both wait on A1 merge (territory: A1 owns
  deploy/daemons/run-daemon-container.sh). /clear before next mandate.
- **dev-4** (ce-dgx-codex local): **A1 shadow harvest-daemon** (ce-ops#388) still mid self-review
  fix cycle at last probe (~970-line diff staged in /var/tmp/ce-388-a1, branch
  ce-388-conveyor-harvest-daemon @ 72cd5bcf pre-fix). Expect READY signal; harvest via LOCAL
  docker-exec bundle (runsc: exec cat, NOT docker cp). Review stop-lines: no approve/merge seams,
  no [Install] in service file; work class likely feature (970 LOC). A1 file-disjoint from S3b ✓.

## EVENT → ACTION MAP
- #785 merge → prune .ce/wt-s3a-harvest + local branch; note INSTALLED_CE_DOGFOOD_MIGRATION.md:42,47,66
  cev3 snippets = queued ce-440-s3c tiny fixup, dispatch ONLY after S3b also merges (file owned by #785 til then).
- dev-1 S3b PR opens → fetch branch + worktree .ce/wt-<n>-review → reviewer (embed: controller
  verified main still had cev3 in both units + test line 39; A1/S3a territory disjoint) → approve on green.
- dev-4 A1 signal → ce-harvest skill → harvest_intake (local bundle; brief MUST carry the
  signed-artifact STOP-line per ce-worker-must-not-sign-ce-root-v1) → review → approve on green.
- A1 merge → dispatch CE-410 slice 10 (publish-reverify-audit; design SSOT = CE410_SLICING_20260703.md
  slice table; re-derive tree_sha pre-push) to freed seat (dev-3 or dev-4, /clear first) → then
  Re-Arming Evidence Bundle assembly → ⏸️ Operator ratification (R1 code-class re-ask per mandate Shape-1).
- S3b + #785 both merged → s3c tiny fixup (3 doc lines) can ride any seat or worker.
- A2 belt containerized canary flip: preconditions in A2_BELT_SHADOW_STAGING_20260704.md
  (OpenBao identity wiring + double-drive sequencing decision) — decision-gated, not seat work.

## WATCHERS (auto-resume on /clear — check TaskList/wait before re-spawning; kill dups keep newest)
b7hq6ib7g PR-board (60s) · b8gyypzb7 seat-signals (40-hex filter; re-fires already-harvested
signals — check before acting) · bk46xs0g8 wall-daemon log.

## MECHANICS (this session, banked)
- dev-1 tmux dispatch needs a SECOND Enter (same as dev-4 herdr) — verify "Working" indicator.
- Harvest worker long-quiet ≠ stalled: check staging worktree tip movement before nudging twice.
- Daemon chain end-to-end proven on #784: review→approve→settle→mint→enqueue→merge ~25 min, zero touches.
- Stale anomaly (unchanged): main checkout on ce-release-0.3.1-rc2, dirty codex-bump files
  (ce-ops#377 territory) — needs deliberate disposition, do not "clean up" casually.

## KEY FILES
Briefs: BRIEF_ce440_s3b_systemd_exec_migration.md (live) · claims: ce-440-s3b-systemd-exec-migration
(+ prior). Worktrees live: .ce/wt-s3a-harvest (prune on #785 merge) · .ce/wt-ce388-shadow (KEEP).
Slicing SSOT: CE410_SLICING_20260703.md · design: CE440_CLI_UNIFICATION_DESIGN_20260704.md.
