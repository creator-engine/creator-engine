# RESUME STATE — CE-DEV-2 — 2026-07-05 ~07:30Z (night-arc checkpoint #4)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260705T0035Z.md. Arc SSOT:
> NIGHTARC_MANDATE_CE_DEV2_20260704_EVENING.md (RATIFIED full-ambition incl. C5 gated cutover).

## ⏸️ AWAITING-OPERATOR
NONE OPEN. All four of the 00:35Z queue items were RESOLVED this session:
1. ✅ CE-410 re-arming — RATIFIED ("ce-410 - ratified as written"); banked
   [[ce-410-rearming-ratified]], bundle doc marked ratified.
2. ✅ N-D OpenBao prereqs — EXECUTED by controller (Operator-authorized). PAT in vault, orphan+
   periodic token ~/.ce-keys/ce-pickup-token, POLICY_SHA
   ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982. [[ce-nd-pickup-openbao-prereqs-done]]
3. ✅ C5 cutover — GO given; ATTEMPT #1 executed + rolled back clean (see N-C below).
4. ✅ #441 bare-`ce` — RATIFIED usage+exit-2, CLOSED. [[ce-bare-ce-usage-decision]]

## MERGED THIS SESSION (12 PRs total this arc-day #782-#795, six of them THIS session)
#792 (A1 fast-follows, 3 review rounds) · #793 (queue-daemon startup lease, 3 rounds incl.
launcher-deadlock + host-check catches) · #794 (daemon-container test gaps) · #795 (ce-446
moved-base resolution) merged. #796/#797/#798 APPROVED + in daemon chain (should merge shortly).

## BOARD (all seats foreman-mode, 3-4 unit pipelines — the fix for the under-utilization the
## Operator flagged; ticket selection currently manual via fleet_recon backlog, to be automated)
- **dev-1** (tmux, self-push, DOUBLE-Enter): finished #446(#795)+#49-skew(#796)+#429(#798);
  NOW on UNIT 4 = ce-435-check-examples-fix (brief /var/tmp, sha in claim). Novelty-check-first.
- **dev-3** (ce-vps-codex): D1 harvested→#797 APPROVED; NOW on D2 = ce-388-d2-pickup-openbao-
  deploy-tests, STACKED on local D1 tip (D1 not yet merged). Then UNIT 3 = ce-415-brownfield.
- **dev-4** (ce-dgx-codex): G9 READY (harvesting) + G10 BLOCKED-transient (harvesting); NOW on
  UNIT 3 = ce-434-contained-seat-profile (the product fix for the false-BLOCKED class).

## IN-FLIGHT HARVESTS (2 background workers running at checkpoint)
- G9 (ce-445-g9-adapter-uid-model @ f5ceefc0) → PR expected `ce-ops#445 G9: adapter uid/ownership`.
- G10 (ce-445-g10-image-daemon-deps @ 4d7e12e2) — seat BLOCKED was a TRANSIENT in-container
  validators/build xdist race; harvest re-runs clean on host. If green → PR; if real → rework.
- Worktrees .ce/wt-ceg9-harvest + .ce/wt-ceg10-harvest ACTIVE — do not prune until their PRs open.

## EVENT → ACTION MAP
- G9/G10 harvest reports → review (uid/ownership fail-closed + tmpfs uid opts for G9; gh-in-image +
  wheelhouse-stage-intact for G10) → approve on green.
- #796/#797/#798 merges → prune claims (ce-49-skew, ce-388-d1-pickup, ce-429). #797 merge → dev-3's
  D2 rebases off its stacked base at harvest; D1's OpenBao code now on main.
- Seat READY signals → harvest → review → approve; every freed thread pulls next POOL item.
- **C5 RETRY** gated on: G9 (uid model) + G10 (gh in image) merged + image REBUILT from that main +
  a stateful-daemon smoke added. Do NOT retry before both land. Full attempt-1 findings +
  one-command block in A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md §C5 ATTEMPT #1.

## N-C C5 CUTOVER — ATTEMPT #1 HALTED, ROLLBACK CLEAN (2026-07-05 ~04:30Z)
Executed in true quiet window (0 open PRs). Host daemon stopped, wall-state migrated, container
launched. HALTED at G9+G10 (uid model + missing gh). Rollback via `bash ~/ce-wall-daemon-launch.sh`
verified — daemon healthy, ~15min downtime zero traffic. PROVEN in-container: #793 supervisor-lease
ancestry-deferral worked first-contact; #791 env-file/cacert/tmpfs plumbing all functioned.
Residual: /home/cedev2/ce-daemon-main/.ce/state chowned 10001:10001 (G9 fix finalizes ownership
model). Daemon worktree /home/cedev2/ce-daemon-main @ origin/main (update at retry).

## POOL (next free thread, ranked; fleet_recon 07:00Z): ce-ops#414 installer.md 0.3.0 paths ·
#417 pilot-runbook fixes · #401 doctrine-coverage fast-follows · #403 confidentiality hardening.
Needs-scoping-first (NOT blind-dispatch): #442 root-key custody (authority-seam) · #419/#420
broker/custody (reserved-adjacent) · #411 (collides dev-1 brain territory until clear).
Deferred tiny: #796 reviewer's 3 non-blocking notes (no-skew test, override-msg order, env-var doc)
· #797 reviewer's --repo-scope-only supplier follow-up.

## GOVERNANCE TICKETS this session: ce-ops#445 (+G9/G10 comments from C5 attempt) · #400/#339
(seat-image dep parity — commented tonight's 2 false-REDs) · #49 (version-skew — quick-win = #796;
3 incidents commented). Recurring theme: nearly EVERY seat "block" this session = in-container
false-RED (ssh-keygen, libsodium, portability guard, build-artifact race) → host preflight green.
That is why #434 + image-dep-parity matter.

## HYGIENE BACKLOG (non-urgent): `git worktree list` shows ~123 stale wt-ce* worktrees from prior
sessions — a real prune pass is overdue (N-E territory). Do carefully; do NOT remove the 2 active
harvest worktrees or the ce-daemon-main cutover worktree.

## WATCHERS (persist across /clear; auto-resume; may look empty for minutes — NEVER re-spawn
## without checking — the PRIOR session's watchers auto-resumed and dup'd mine this session):
b7hq6ib7g PR-board · b8gyypzb7 seat-signals · bk46xs0g8 (aka bzlkhyasz replaced) wall-daemon log.

## MECHANICS banked: foreman queue-adds via "FOREMAN QUEUE - UNIT N, do not interrupt, after
## <condition> read <brief> verify sha=<>" (herdr single-quote-safe: pass via var not inline parens) ·
reviewer brief must say "author=seat X, you are the independent reviewer" (else Sonnet returns
COMMENT not APPROVE on 'self-push' misread) · brain-pinned-artifact edit needs 3 pre-auths
[[ce-brain-supersession-brief-checklist]] · contained-seat BLOCKED-with-clean-commit = harvest
trigger, host preflight is arbiter · daemon chain approve→merge ~15-25min.
