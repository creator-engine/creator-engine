# RESUME STATE — CE-DEV-2 — 2026-07-04 ~23:00Z (night-arc checkpoint #2)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260704T1840Z.md. Arc SSOT:
> NIGHTARC_MANDATE_CE_DEV2_20260704_EVENING.md (RATIFIED full-ambition incl. C5 gated cutover).

## ⏸️ AWAITING-OPERATOR (surface FIRST, in this order)
1. **CE410_REARMING_BUNDLE_20260704.md** — ready for ratification (form-echo text inside).
2. **N-D OpenBao deployment prereqs** (ND_REVIEW_PICKUP_OPENBAO_WIRING_DESIGN_20260704.md §⏸️):
   vault PAT at ce-kv/forge/ce-dev-2/gh-token · periodic-orphan BAO token · policy-sha doc ·
   CE_OPENBAO_ALLOWED_REFS. Code lands without these.
3. C5 cutover: if not executed overnight (gates), it is one-command staged — see
   A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md runbook.

## MERGED TONIGHT (night-arc): #787 (s3b) · #788 (s10 → CE-410 CODE-COMPLETE, all 10 slices) ·
#790 (s3c — CE-440 docs surface COMPLETE, only S4-at-release remains) · #789 (G8 Dockerfiles,
merged-pending at checkpoint: marker minted, enqueue imminent; ONE rework round — reviewer caught
build-image.sh staged-context omission of wheelhouse-dev; fixed at 37b66ff8).
Day+evening total: #782-#790, nine PRs, all via the zero-touch chain.

## BOARD (all Working; signals = READY-FOR-HARVEST <slug> <40hex>)
- **dev-1**: ce-445-c2-daemon-container-plumbing (G3-G6: CE_DAEMON_ENV_FILE 0600-guarded,
  CE_DAEMON_CACERT_FILE ro-mount, tmpfs secret custody, byte-identical backwards-compat test).
  Brief /var/tmp/BRIEF_ce445_c2_daemon_container_plumbing.md sha=de5c70c0…. Self-pushes PR.
- **dev-3**: ce-388-fastfollow-lease-ux (#443) — STILL RUNNING (longest unit; if idle-probe shows
  done-but-unsignaled, check /var/tmp worktree before re-dispatching). Brief sha=9e83420d….
- **dev-4**: ce-444-queue-daemon-startup-lease (C3; v3_cli lease, exit 73, lease-on-dry-run,
  RUNBOOK note). Brief /var/tmp/BRIEF_ce444_queue_daemon_startup_lease.md sha=d76314673….
- N-D **D1 SERIALIZED after C3 merges** (both touch v3_cli.py); D2 after D1. Design SSOT banked.

## EVENT → ACTION MAP
- #789/#790 merge → prune .ce/wt-789-review + .ce/wt-790-review (+ any wt-789-review2) + local
  branches (ce-445-g8-…, ce-440-s3c-…).
- dev-1 C2 PR → fetch+worktree wt-<n>-review → reviewer (embed: backwards-compat is the hard bar;
  tmpfs custody restores /dev/shm semantics; env-file 0600 refusal) → approve on green.
- dev-3 signal → harvest (VPS bundle-stream) → review (stop-lines: forbidden-strings guard intact;
  --dry-run now ERRORS pointing to --one-shot; RUNBOOK product-lens) → approve on green.
- dev-4 signal → harvest (local exec-cat bundle) → review (lease default-on incl. dry-run; exit 73
  consistency; no conveyor files touched) → approve on green → THEN dispatch D1 (OpenBao supplier,
  design SSOT ND_REVIEW_PICKUP…md, slices D1 story) to freed seat.
- C2+C3+#789 all merged → C4 cutover preflight dry-run (staging doc §runbook step 1) → C5 ONLY if
  all gates (incl. zero in-flight PRs + ≥2h quiet + kill-switch verified), else stage for morning.
- Rebuild image from post-G8 main as post-merge verification of the Dockerfile fix (was briefed as
  controller follow-up): `sudo docker buildx build -f deploy/runtime-image/Dockerfile --platform
  linux/arm64 --tag creator-engine/ce-validator:0.3.1 --load <repo-root-worktree-at-main>` should
  now succeed WITHOUT workaround. Do in a quiet moment; ~10 min.

## WATCHERS: b7hq6ib7g PR-board · b8gyypzb7 seat-signals (re-fires stale signals — cross-check
claims/PRs) · bk46xs0g8 wall-daemon log. All persist/auto-resume; don't duplicate.

## TICKETS tonight: #442 custody · #443 (dev-3 implementing) · #444 (dev-4 implementing) · #445
(G8 fixed via #789; C2 in-flight; G2 registry-publish deliberately out of scope).
## Incidents/mechanics: see prior checkpoint (1840Z) — root-key STOP-line now standard in briefs;
herdr in-container w/ -e HERDR_SOCKET_PATH; double-Enter on all seat sends.
