# BRIEF — ce-445-c2 — daemon-container launcher plumbing (env-file, CA cert mount, tmpfs secret custody)

Role: implementer (dev-1 self-push). Branch: `ce-445-c2-daemon-container-plumbing` off freshly-fetched
origin/main.

## Problem (controller recon, embedded — deployment gaps for the containerized merge-gate cutover)
deploy/daemons/run-daemon-container.sh is the container adapter for queue-daemon (and now
conveyor-daemon). Three gaps block a real cutover on the controller host:
- **G3/G5 env delivery**: the container form requires CE_GATE_REPO + CE_GATE_AUTHORIZED_REVIEWERS
  (+GH_TOKEN, BAO_*) as env vars via add_env_if_present — i.e. the CALLER must export everything.
  There's no first-class env-file path, so host launches depend on ad-hoc exports.
- **G4 CA cert**: BAO_CACERT is forwarded as an env var pointing at a HOST path
  (/usr/local/share/ca-certificates/…) that does not exist inside the container; no mount provision.
- **G6 secret custody regression**: the host daemon writes the approval-wall secret to tmpfs
  (/dev/shm, memory-only, deliberate). The container form writes it under the DISK-backed state
  mount (<state_root>/queue-daemon/approval-wall-secret). Memory-only custody must be restored.

## Deliverable — extend run-daemon-container.sh (backwards-compatibly)
1. `CE_DAEMON_ENV_FILE` (optional): when set, validate the file exists with mode 0600 (refuse
   otherwise — it carries tokens) and pass `--env-file "$CE_DAEMON_ENV_FILE"` to the engine run.
   Explicit env vars (add_env_if_present) still win where both are present (document the
   engine's precedence in a comment).
2. `CE_DAEMON_CACERT_FILE` (optional): when set, mount it read-only at a fixed container path
   (e.g. /ce/etc/openbao-ca.crt) and set BAO_CACERT to that container path (overriding any
   host-path value that would dangle inside the container).
3. tmpfs custody: for the queue-daemon arm, mount a tmpfs at the directory holding
   CE_APPROVAL_WALL_SECRET_TARGET_FILE (e.g. `--tmpfs /ce/state/queue-daemon-secret:rw,size=1m,mode=0700`
   and repoint CE_APPROVAL_WALL_SECRET_TARGET_FILE there) so the materialized secret never touches
   disk. Apply the same pattern to the conveyor-daemon arm's signing-secret file mount if present.
4. Tests: find the existing test coverage for run-daemon-container.sh (grep validators/tests for
   the filename; test_gate_daemons_systemd.py asserts unit files, there may be a daemons-script
   test) and extend it: env-file refusal on bad mode, cacert mount arg construction, tmpfs arg
   present for queue-daemon, and — critically — the EXISTING queue-daemon invocation without any
   new vars set must produce byte-identical engine args (backwards-compat regression test).

## Constraints
- Files (closed set): deploy/daemons/run-daemon-container.sh · the test file(s) you identify
  (name them in the carrier) · .ce/changelog/ce-445-c2-daemon-container-plumbing.md ·
  .ce/pr-manifests/ce-445-c2-daemon-container-plumbing.md.
- Do NOT touch: Dockerfiles (in-flight PR #789), deploy/conveyor-daemon/launch-conveyor-daemon.sh
  (claimed by dev-3), deploy/systemd/, v3_cli.py (claimed by dev-4), any signed artifact.
- Backwards compatibility is a hard bar: existing callers with no new env vars set must get
  byte-identical behavior.
- ⛔ Signed-artifact stop-line: signature-gate failure → STOP + report bytes; never sign.
- Work class: story. Bounded ≤ ~250 LOC.

## Preflight
FULL `ce validate-pr` GREEN one pass before push.

## PR + evidence
PR to main, title `deploy: daemon-container env-file, CA-cert mount, and tmpfs secret custody`.
Body: exactly one `- **Declared work class:** story` line + note "Closes plumbing gaps G3-G6 on the
containerized-cutover staging doc." Signal: `READY-FOR-HARVEST ce-445-c2-daemon-container-plumbing <sha> PR #<n>`.

## Stop line
No approve/merge/enqueue/self-review. Controller reviews.
