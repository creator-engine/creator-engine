# A2 queue-daemon containerized cutover — staging fact base (recon 2026-07-04 ~18:10Z)
> Executes ratified A2-SEQ Option A (see A2_DOUBLE_DRIVE_SEQUENCING_DECISION_20260704.md).
> Verdict: CUTOVER BLOCKED on G1/G2/G7 (image) + G3-G6 (plumbing). Full recon in session task
> afe865a4f36b88d85 output; distilled here.

## Blocking gaps (ticket = ce-ops#445; C1 update 2026-07-04 ~19:00Z)
- **G1/G7 — image: ✅ CLOSED for local cutover.** Built natively on DGX: arm64, sha256:66fedb4e…,
  smoke green (ce + cev3 --help), context origin/main@3a930d05, canonical path =
  deploy/runtime-image/Dockerfile (NOT deploy/oci). Base digest = proper OCI index w/ arm64 (no
  #377 hazard).
- **G8: ✅ CLOSED** — #789 merged (incl. build-image.sh staging fix caught in review) + post-merge
  VERIFIED: clean rebuild from main@86db902e, tracked Dockerfile zero-edits, arm64, image
  sha256:1923e121…, smoke green, dry-run stages wheelhouse-dev.
- **G3-G6: ✅ CLOSED** — #791 merged (CE_DAEMON_ENV_FILE 0600-guarded; CE_DAEMON_CACERT_FILE
  ro-mount + BAO_CACERT repoint; tmpfs secret custody both arms — memory-only restored;
  byte-identical no-new-vars compat test).
- **G2 — registry publish**: still open, deliberately out of night-arc scope (reserved).

## C4 PREFLIGHT READINESS (2026-07-04 ~22:00Z): repo side COMPLETE.
Remaining before C5: host env file staged 0600 w/ G3 vars + BAO_* (host op, use CE_DAEMON_ENV_FILE)
· kill-switch re-verify · #444 lease (in impl, nice-to-have not gate) · zero in-flight PRs + ≥2h
quiet window (unlikely before the tail of tonight's queue — else stage for morning).
- **G3 — env contract mismatch**: container form requires CE_GATE_REPO + CE_GATE_AUTHORIZED_REVIEWERS
  as ENV (validate_required_env); host launcher passes them only as --repo/--authorized-reviewer argv.
- **G4 — BAO_CACERT not mounted**: env forwarded but host path
  /usr/local/share/ca-certificates/ce-openbao-ca.crt not mounted into the container; script has no
  cacert mount provision.
- **G5 — no env file on DGX**: /etc/creator-engine/ absent here (unit written for VPS, User=ce-dev-1).
- **G6 — secret target path changes**: host daemon writes tmpfs /dev/shm/ce-wall-daemon/secret;
  container form writes disk-backed <state_root>/queue-daemon/approval-wall-secret. Runbook must
  (a) confirm no external reader depends on the /dev/shm path, (b) prefer restoring tmpfs semantics
  (mount a tmpfs at the container secret dir) — memory-only custody was deliberate.

## Not gaps
Docker+runc fine on aarch64 (no runsc dependency in the daemon script); podman 4.9.3 available as
drop-in via CE_CONTAINER_ENGINE=podman (ratified tier-split prefers rootless podman for
validation/PCO-class workloads — engine choice for the gate daemon = runbook decision, default docker/runc first, podman migration later with #439).

## Cutover runbook skeleton (execute ONLY when gaps closed + quiet window)
1. Preflight: image present + arm64 (`docker image inspect --format '{{.Architecture}}'`); env file
   staged (0600, all G3 vars + BAO_*); cacert mount flag available; tmpfs secret mount decided;
   in-flight PR set empty or accepted-risk; kill-switch launcher verified runnable.
2. Stop host daemon (kill PID from pgrep queue-daemon; confirm no process).
3. Start container form: run-daemon-container.sh queue-daemon with env file; verify
   daemon_pass_start/complete in logs within 2 intervals (240s); verify a real decision matches
   expectation on a test PR or observed skip reasons.
4. Soak ≥3 arc-days green (wall-daemon log watcher retargeted at container logs).
5. Rollback at ANY anomaly: stop container → bash ~/ce-wall-daemon-launch.sh (restores tmpfs path).
6. After soak: decommission decision for host launcher (keep as documented cold-standby per
   Option A; do NOT delete).

## Sequencing note
Gap-closure work (image build + launcher plumbing PRs) is seat-dispatchable now (file-disjoint
check vs in-flight ce-410-s10 / ce-388-fastfollow / ce-440-s3b required — run-daemon-container.sh
is FREE post-#786 but conveyor fast-follow (dev-3) touches launch-conveyor-daemon.sh, NOT the
shared runner script; verify at dispatch time).

## ✅ C5 OPERATOR GO (2026-07-05 ~03:05Z, in-session)
Operator: "C5 cutover is go, you are authorized to execute when ready." Execution discipline
unchanged: drain in-flight PR traffic first (no gate swap under live PRs), stage host env file
0600 (CE_DAEMON_ENV_FILE) + CE_DAEMON_CACERT_FILE, re-verify kill-switch launcher, stop host
daemon → run-daemon-container.sh queue-daemon → watch 2 passes green; ANY anomaly → rollback
`bash ~/ce-wall-daemon-launch.sh` + halt + ⏸️ note. Soak day 1 of 3 starts at cutover.

## C4 HOST-SIDE PREFLIGHT ✅ STAGED (2026-07-05 ~05:5xZ) — cutover is one command
Verified/staged by CE-DEV-2:
- Image: creator-engine/ce-validator:0.3.1 present, arm64, sha256:1923e121… (post-G8 clean rebuild). ✅
- Env file: ~/.ce-keys/ce-daemon-container.env (0600, 16 vars: GH_TOKEN, BAO_TOKEN, BAO_ADDR,
  CE_GATE_*, CE_OPENBAO_KV_MOUNT, all CE_APPROVAL_WALL_* incl. both policy shas, interval). ✅
- Kill-switch: ~/ce-wall-daemon-launch.sh syntax-verified; token file present 0600. ✅
- CA cert: /usr/local/share/ca-certificates/ce-openbao-ca.crt present → CE_DAEMON_CACERT_FILE. ✅
- ⚠️ TWO ADAPTER FACTS the skeleton missed (controller-verified from the script):
  1. The adapter mounts CE_DAEMON_REPO_ROOT (default = script's own repo) :ro and runs
     deploy/queue-daemon/launch-queue-daemon.sh FROM THE MOUNT — the main checkout here is on the
     rc2 branch, so a dedicated clean worktree is staged: /home/cedev2/ce-daemon-main @ origin/main
     (86db902e). UPDATE IT (git -C … fetch+reset origin/main) at cutover so it includes #792/#793.
  2. Container wall-state path = <state_root>/queue-daemon/approval-wall-state.json ≠ host daemon's
     .ce/state/approval-capability-wall/state.json → COPY the state file over at cutover (after
     stopping the host daemon, before starting the container).
- tmpfs custody: set CE_APPROVAL_WALL_SECRET_TARGET_FILE non-empty at launch → adapter mounts a
  1m tmpfs and repoints the target (memory-only custody preserved).

### Cutover command block (execute in quiet window; zero in-flight PRs)
```bash
git -C /home/cedev2/ce-daemon-main fetch -q origin main && git -C /home/cedev2/ce-daemon-main reset -q --hard origin/main
kill <pid-of queue-daemon from pgrep -f 'v3_cli queue-daemon'> && sleep 3 && ! pgrep -f 'v3_cli queue-daemon'
install -d -m 0700 /home/cedev2/ce-daemon-main/.ce/state/queue-daemon
cp /home/cedev2/creator-engine/.ce/state/approval-capability-wall/state.json /home/cedev2/ce-daemon-main/.ce/state/queue-daemon/approval-wall-state.json
CE_DAEMON_REPO_ROOT=/home/cedev2/ce-daemon-main \
CE_DAEMON_ENV_FILE=$HOME/.ce-keys/ce-daemon-container.env \
CE_DAEMON_CACERT_FILE=/usr/local/share/ca-certificates/ce-openbao-ca.crt \
CE_APPROVAL_WALL_SECRET_TARGET_FILE=tmpfs \
nohup bash /home/cedev2/ce-daemon-main/deploy/daemons/run-daemon-container.sh queue-daemon --loop >> ~/ce-wall-daemon-container.log 2>&1 &
# watch 2 passes (240s): daemon_pass_start/complete in ~/ce-wall-daemon-container.log; retarget log watcher.
# ROLLBACK: docker stop ce-queue-daemon; bash ~/ce-wall-daemon-launch.sh
```
(--loop arg form: confirm the adapter's daemon_cmd passthrough at execution; launch-queue-daemon.sh
may loop by default — verify before running.)

## ⏸️ C5 ATTEMPT #1 — 2026-07-05 ~04:30-04:45Z — HALTED per discipline, ROLLBACK CLEAN
Executed in a true quiet window (0 open PRs). Host daemon stopped, state migrated, container
launched. Halted at three stacked gaps; rollback via kill-switch launcher verified (daemon back,
passes green, ~15 min gate downtime with zero traffic).

**Gaps found (all filed on ce-ops#445):**
- **G9 — adapter uid model**: canonical image runs as uid 10001 (`ce`); adapter mounts host state
  root and its own host-side `install -d -m 0700` runs as the invoking user. Host-owned 0700 dir →
  container user can't write; chown to 10001 → adapter's host-side chmod fails. The `--tmpfs`
  secret mount is root-owned (unwritable for 10001) — needs `uid=10001,gid=10001` opts. Adapter
  implicitly assumes invoking-uid == container-uid (rootless-podman-shaped); with docker it
  contradicts itself. Fix = ownership/uid handling in the adapter + tmpfs uid opts (+ runbook).
- **G10 — image missing gate-daemon runtime deps**: first real daemon pass failed closed
  `[Errno 2] No such file or directory: 'gh'`. The canonical runtime image never shipped the gh
  CLI (validators-only content). Same gap class as the seat-image ssh-keygen/libsodium issue
  (ce-ops#400/#339). Fix = audit gate-daemon runtime deps (gh, git, …) into the runtime image.
- Adapter's `--help` smoke tests + oci dry-run never exercised a stateful daemon run — that's why
  C4 "repo-side complete" missed all three. Add a stateful smoke to the preflight before retry.

**Positive findings:** #793's supervisor-lease + ancestry-deferral worked PERFECTLY in the
container on first contact (supervisor acquired lease, CLI deferred with the correct log line);
state migration + env-file + CA-cert mount + wall-secret plumbing all functioned; a real
daemon_pass_start fired inside the container.

**Residual host state:** /home/cedev2/ce-daemon-main/.ce/state is chowned 10001:10001 (left for
the retry; the G9 fix decides final ownership model). Retry after G9+G10 merge + image rebuild.

## ⏸️ C5 ATTEMPT #2 — 2026-07-06 ~02:45Z — HALTED host-side, ROLLBACK CLEAN (~4 min, zero traffic)
Post-G9/G10 retry: image rebuilt from post-0.3.2 main (creator-engine/ce-runtime:0.3.2-main,
sha256:27135d39…, arm64, gh+git in, #805 smoke GREEN w/ uid-1003 adaptation). Host daemon
stopped, wall-state migrated. Adapter exited 1 HOST-SIDE before any container start: its own
`install -d` vs the 10001-owned/0700 state root (attempt-#1 residual = production ownership)
fails as invoking uid 1003. G9 fix missed the pre-owned re-run path; #805 smoke masks it by
adapting the whole contract to the caller's uid. Secondary: shared append log interleaved
attempt-#1 lines (stale 'gh not found' nearly misled); adapter default image tag
ce-validator:0.3.2 nonexistent (CE_DAEMON_IMAGE explicit; honor unverified — container never
launched). Findings ticket filed (see ce-ops, references #445/#799/#800/#805). Rollback:
`bash ~/ce-wall-daemon-launch.sh` → pid 200363, passes green; daemon stdout now at the
session scratchpad rollback-relaunch.log (log watcher retargeted). Wall-state copy in
ce-daemon-main left in place for attempt #3. Retry gates: adapter mixed-uid host-prep fix +
mixed-uid smoke variant + per-attempt logs. Soak clock reset.

**pgrep footgun (controller lesson):** `pgrep -f 'v3_cli queue-daemon'` self-matches the
checking shell's own command line → two false "daemon still running" aborts. Check via
`ps aux | grep … | grep -v "bash -c"` or match the exact binary path string absent from the
probe's own argv.
