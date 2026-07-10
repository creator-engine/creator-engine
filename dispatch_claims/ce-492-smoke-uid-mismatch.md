# WORK CLAIM — ce-492-smoke-uid-mismatch
claimed: 2026-07-09T06:4xZ (fleet restock batch dev-4; ce-ops#492)
seat: dev-4 (ce-dgx-codex, contained commit-only)
branch: ce-492-smoke-uid-mismatch
paths: deploy/daemons/smoke-daemon-container.sh (modify: chown in write_secret_file + pass-log dump in cleanup before rm -rf) + changelog + carrier
brief: .ce/briefs/BRIEF_dev4_restock_batch_20260709.md
constraints: no brain assertions.yaml touch; only write_secret_file and cleanup functions; bash -n syntax check required; COMMIT-ONLY
