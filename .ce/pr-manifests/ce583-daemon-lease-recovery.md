# PR path manifest — ce-ops#583 · Queue daemon lease recovery hardening

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce583-daemon-lease-recovery` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=90e77a8a026cca85b5b9b0e75883736fd25ffcdc298743682aa0fab0585859d0

```text
.ce/changelog/ce583-daemon-lease-recovery.md
.ce/pr-manifests/ce583-daemon-lease-recovery.md
deploy/queue-daemon/launch-queue-daemon.sh
validators/creator_engine_validator/daemon_lease.py
validators/tests/unit/test_daemon_lease.py
```
