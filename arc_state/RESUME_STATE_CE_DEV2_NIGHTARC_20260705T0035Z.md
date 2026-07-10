# RESUME STATE — CE-DEV-2 — 2026-07-05 ~00:35Z (night-arc checkpoint #3; pre-/clear, ctx 38%)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260704T2300Z.md. Arc SSOT:
> NIGHTARC_MANDATE_CE_DEV2_20260704_EVENING.md (RATIFIED full-ambition incl. C5 gated cutover).

## ⏸️ AWAITING-OPERATOR (surface FIRST, this order — Operator was given this list ~00:30Z)
1. **CE-410 re-arming ratification** — CE410_REARMING_BUNDLE_20260704.md (form-echo text inside;
   13/13 evidence, 7/7 substantive gate-adjacent reviews). Does NOT grant code-class auto-approve.
2. **N-D OpenBao prereqs** (~15 min console): PAT → ce-kv/forge/ce-dev-2/gh-token · periodic-orphan
   BAO token (read path+metadata + sys/audit) · policy doc → sha for --pickup-token-secret-ref-policy-sha ·
   CE_OPENBAO_ALLOWED_REFS. SSOT: ND_REVIEW_PICKUP_OPENBAO_WIRING_DESIGN_20260704.md §⏸️.
3. **C5 cutover go** (if not executed overnight): one-command-ready per
   A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md (repo side COMPLETE; see below).
4. Policy decisions when convenient: #395 tag-timing (dev-1 drafting options now) · ce-ops#441 bare-`ce`.

## MERGED (this arc-day, all zero-touch chain): #782-#791 = ELEVEN PRs.
- CE-410 CODE-COMPLETE (all 10 slices; bundle staged ⏸️).
- CE-440 docs surface COMPLETE (S1/S2/S3a/S3b/s3c; only S4 rides the next signing event).
- Containerized-gate repo side COMPLETE: image G1/G7/G8 ✅ (clean rebuild VERIFIED from
  main@86db902e, tracked Dockerfile zero-edits, arm64, image sha256:1923e121…, ce+cev3 smoke green,
  oci dry-run stages wheelhouse-dev) + plumbing G3-G6 ✅ (#791). G2 registry publish = reserved.

## BOARD (dispatched pointer+SHA, Working-verified at dispatch)
- **dev-1** (tmux ce-dev1-orchestrator:2.0; DOUBLE-Enter on sends): ce-395-tag-timing-policy —
  policy DRAFT (options + recommended default, decision marked OPERATOR-DECISION; semantic novelty
  check vs ticket state first; may signal BLOCKED already-resolved). Brief
  /var/tmp/BRIEF_ce395_tag_timing_policy.md sha=26f4e0ce…. Self-pushes PR.
- **dev-3** (ce-vps-codex via ssh dev1; herdr IN-CONTAINER `-e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock`):
  ce-388-fastfollow-lease-ux (#443) — LONGEST-RUNNING unit (dispatched ~17:40Z). If idle w/o signal:
  probe /var/tmp worktree for done-but-unsignaled BEFORE re-dispatch. Brief sha=9e83420d….
- **dev-4** (ce-dgx-codex local, same herdr pattern): ce-444-queue-daemon-startup-lease (C3) —
  near done at last probe (v3_cli.py +76, test_integrator_belt.py +147, RELOCATION.md +8 staged).
  Brief sha=d7631467…. Contained → harvest via exec-cat bundle on signal.

## EVENT → ACTION MAP
- dev-4 C3 signal → ce-harvest skill → harvest_intake (local bundle) → review (lease default-on
  incl. dry-run; exit 73 consistency; no conveyor files; tests in test_integrator_belt.py is FINE —
  no collision, dev-1's launcher tests live in test_daemon_lease.py) → approve on green →
  **THEN dispatch N-D D1** (OpenBao supplier+flags+loop-refresh, story; design SSOT
  ND_REVIEW_PICKUP_OPENBAO_WIRING_DESIGN_20260704.md; v3_cli.py freed by C3 merge) to the freed
  seat; D2 (unit+env-docs+tests) after D1.
- dev-3 signal → harvest (VPS bundle-stream) → review (forbidden-strings guard intact; --dry-run
  ERRORS pointing to --one-shot; RUNBOOK product-lens) → approve on green.
- dev-1 #395 PR → fetch+worktree+reviewer (draft-quality lens: options complete, default
  recommended, NO policy implemented ahead of ratification) → approve on green.
- All three merged + zero in-flight + ≥2h quiet + kill-switch verified → C5 cutover per staging
  doc (host env file 0600 via CE_DAEMON_ENV_FILE + CE_DAEMON_CACERT_FILE + stop host daemon →
  run-daemon-container.sh queue-daemon → 2-pass watch → rollback = bash ~/ce-wall-daemon-launch.sh).
  Gates not met → stage + ⏸️ note. Lease (#444) = nice-to-have, not a C5 gate.
- Tail items (only if a seat truly idles): #446 CI shallow-fetch fix (ticketed w/ options) ·
  #791 review's 3 non-blocking test gaps · close-bot #262 · L3 apply-mode.

## HYGIENE QUEUE (cheap, any quiet moment)
- Prune stale claims of MERGED work in .ce/claims/: ce-440-s3b, ce-440-s3c, ce-410-s10, ce-445-g8,
  ce-445-c2, ce-388-conveyor-harvest-daemon, ce-440-s3a (keep: ce-395, ce-388-fastfollow, ce-444).
- Stale anomaly UNCHANGED (do not casually clean): main checkout on ce-release-0.3.1-rc2 + dirty
  codex-bump files = N-E disposition item (ce-ops#377 territory), still pending deliberate handling.

## WATCHERS (persist across /clear; auto-resume; TaskList may look empty for minutes — NEVER
re-spawn without checking): b7hq6ib7g PR-board · b8gyypzb7 seat-signals (re-fires stale signals —
cross-check vs claims/merged PRs) · bk46xs0g8 wall-daemon log.

## TICKETS this arc-day: #442 root-key custody (incident: harvest worker self-signed on #785;
STOP-line now in every signed-artifact brief — memory ce-worker-must-not-sign-ce-root-v1) ·
#443 (dev-3 implementing) · #444 (dev-4 implementing) · #445 (all gaps closed except G2) ·
#446 CI shallow-fetch moved-base flake (stalled #789 ~1h; re-run fixed; recurs at merge cadence).

## MECHANICS (banked in memory, quick refs): herdr in-container + -e SOCKET + double-Enter ·
dev-1 tmux double-Enter · daemon chain approval→merge ~15-25 min, governance_check_not_success
right after push/merge = propagation lag or the #446 flake (check for a SECOND failing run on the
same head before assuming content failure) · reviewer briefs embed controller-verified main-side
facts · fetch+worktree BEFORE reviewer dispatch · carrier stem == branch · gate vocab
tiny|story|feature|epic.
