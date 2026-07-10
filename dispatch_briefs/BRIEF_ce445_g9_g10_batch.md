# BATCH BRIEF — ce-445 G9 + G10 — containerized-gate cutover gaps (two file-disjoint units)

Role: implementer (dev-4, contained, foreman mode — run BOTH units as separate branches/worktrees;
they are file-disjoint from each other and from all in-flight work). Each branch off freshly-fetched
origin/main. Worktrees under /var/tmp. venv: `.venv/bin/python -m pytest`, PYTHONPATH=validators,
TMPDIR=/var/tmp.

## Context (embedded — controller evidence from the first real cutover attempt, 2026-07-05 ~04:30Z)
The containerized queue-daemon was launched for real on the DGX (docker, canonical image
creator-engine/ce-validator:0.3.1, which runs as uid 10001 user `ce`). Three findings:
(a) uid mismatch: host-owned 0700 state dir → in-container `install -d` fails
    `install: cannot create directory '/ce/state': Permission denied`; chowning the host tree to
    10001 makes the ADAPTER's own host-side `install -d -m 0700` fail as the invoking user.
(b) the `--tmpfs /ce/state/queue-daemon-secret:rw,size=1m,mode=0700` mount is root-owned inside
    the container — unwritable for uid 10001; needs `uid=10001,gid=10001` mount options.
(c) with (a)+(b) worked around, the daemon started, the supervisor lease + ancestry deferral
    worked, a real pass fired — then failed closed: `[Errno 2] No such file or directory: 'gh'`.
    The image never shipped the gh CLI, which queue-daemon execs for every PR operation.

---

## UNIT 1 — ce-445-g10-image-daemon-deps (dispatch FIRST; tiny/story)
Branch: `ce-445-g10-image-daemon-deps`.
Deliverable: the canonical runtime image must carry every runtime dependency the gate daemons
exec. AUDIT first: grep the queue-daemon + conveyor-daemon code paths
(validators/creator_engine_validator/{v3_cli.py,integrator_belt.py,conveyor_daemon*.py,forge/}) for
subprocess/exec targets (`gh`, `git`, anything else). Then:
1. deploy/runtime-image/Dockerfile: install the missing deps in the RUNTIME stage (gh = GitHub CLI —
   install from the official apt repo pinned by keyring, arm64+amd64 safe; git if absent). Keep the
   offline/wheelhouse build properties intact (the wheel-builder stage constraints from the
   clean-pull fix must not regress).
2. deploy/oci/Dockerfile: same additions.
3. If a Dockerfile-content test exists (check validators/tests for tests asserting Dockerfile
   content), extend it to pin the new deps; name any test file in the carrier.
Files (closed set): deploy/runtime-image/Dockerfile · deploy/oci/Dockerfile · (existing
Dockerfile-content test file if any) · changelog · carrier.
Commit: `ce-ops#445 G10: bundle gate-daemon runtime deps (gh) into the canonical image`.

## UNIT 2 — ce-445-g9-adapter-uid-model (story)
Branch: `ce-445-g9-adapter-uid-model`.
Deliverable: make deploy/daemons/run-daemon-container.sh correct for docker (no userns remap)
while staying podman-compatible. Required properties (fail-closed, no silent weakening):
1. Declare the image runtime uid as a constant (CE_DAEMON_IMAGE_UID default 10001) with a comment
   that it is the canonical image's contract.
2. Host-side state prep: create state/lease roots only when MISSING; when they exist, VERIFY
   usability instead of unconditionally chmod-ing (the current `install -d -m 0700` fails as a
   non-owner even when the dir is already correct). If ownership doesn't match what the container
   user needs (uid mismatch under docker), DIE with a clear, copy-pasteable remediation
   (`chown -R <uid>:<uid> <state_root>` runbook line) — do not silently chown.
3. Add `uid=<uid>,gid=<uid>` options to BOTH tmpfs mounts (queue secret dir + conveyor secret dir).
4. Update the byte-identical default-invocation pin tests in
   validators/tests/unit/test_daemon_lease.py (queue + conveyor pins) for the argv change —
   deliberate pin update, note it in the changelog. Add behavioral tests for: missing-state-root
   → created; existing-but-wrong-ownership → clean die with remediation text (simulate with a
   root-owned dir is not possible in tests — simulate with a dir owned by another uid only if
   feasible; otherwise test the verification branch via a mode/ownership check seam).
Files (closed set): deploy/daemons/run-daemon-container.sh · validators/tests/unit/test_daemon_lease.py ·
changelog · carrier.
Commit: `ce-ops#445 G9: adapter uid/ownership model for docker + tmpfs uid opts`.

---

## Shared constraints
- Units must not touch each other's files, nor: .github/workflows/ (dev-1 territory),
  validators/creator_engine_validator/{secret_identity.py,v3_cli.py,forge/review_pickup.py}
  (dev-3 territory), launch-queue-daemon.sh, launch-conveyor-daemon.sh.
- ⛔ Signed-artifact stop-line: any SSHSIG/SHA256SUMS/content_sha256 gate failure → STOP and
  report; never sign; ce-root-v1 is controller-only.
- Preflight: FULL `ce validate-pr` per branch; known container env gaps (ssh-keygen, libsodium)
  may false-RED — if the ONLY failures are those gates AND your touched-module tests pass, signal
  with the PREFLIGHT-NOTE.
- Work class per branch: minimal compliant. Changelog + carrier per branch (stem == branch).

## Evidence + signal (per unit; no push — controller harvests)
`READY-FOR-HARVEST <branch> <40-hex sha>` (+ ` PREFLIGHT-NOTE envgap:<gates>` if applicable).
Emit Unit 1's signal as soon as it's done — do not hold it for Unit 2.

## Stop line
No push, no PR, no review, no signing. Controller harvests on signal.
