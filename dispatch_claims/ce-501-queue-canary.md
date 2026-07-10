# WORK CLAIM — ce-501-queue-canary

- seat: dev-1 (self-push lane, VPS host, non-contained)
- dispatched: 2026-07-09 by CE-DEV-2 controller
- brief: .ce/briefs/BRIEF_dev1_restock_batch_20260709.md (unit U1)
- ticket: ce-ops#501
- branch: ce-501-queue-canary
- worktree: ~/creator-engine-ce-501-queue-canary (off origin/main @ add00a60e)
- work class: S

## Claimed paths

- deploy/queue-daemon/launch-queue-daemon.sh (existing, modify — add CE_QUEUE_DAEMON_CANARY=1 mode)
- validators/tests/unit/test_queue_daemon_canary_launch.py (new)
- .ce/changelog/ce-501-queue-canary.md (new)
- .ce/pr-manifests/ce-501-queue-canary.md (new)
- .ce/wt-ce501/READY or .ce/wt-ce501/BLOCKED (signal)

## Scope summary

Adds CE_QUEUE_DAEMON_CANARY=1 mode to deploy/queue-daemon/launch-queue-daemon.sh: implies
--dry-run, omits all --approval-wall-secret-* flags (wall resolves DORMANT legitimately),
relaxes required-env to GH_TOKEN+CE_GATE_REPO+CE_GATE_AUTHORIZED_REVIEWERS only, refuses
if CE_DAEMON_STATE_ROOT conflicts with the live daemon default, emits CANARY MODE banner.
No Python changes (v3_cli.py already handles DORMANT when no backend configured).

## Explicit exclusions

- .ce/brain/assertions.yaml (PR #918 exclusive — BRAIN-LEDGER-BUSY)
- deploy/vps-runsc/run-vps-runsc.sh (PR #918)
- deploy/dgx-runsc/run-codex-runsc.sh (PR #918)
- validators/creator_engine_validator/v3_cli.py (no change needed)
- deploy/daemons/smoke-daemon-container.sh (dev-4 in-flight)

## Signal expected

PR <number> ce-501-queue-canary (non-draft, ready-for-review)
