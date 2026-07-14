# PR path manifest — ce-ops#554 · Queue-daemon restart lease recovery

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-554-queue-daemon-restart-lease` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0b7f7a6f68fad3ea65aa6de2f76af217a38c1fc094ce124dc1df0e0acb906d01

```text
.ce/changelog/ce-554-queue-daemon-restart-lease.md
.ce/pr-manifests/ce-554-queue-daemon-restart-lease.md
deploy/daemons/README.md
deploy/queue-daemon/launch-queue-daemon.sh
validators/tests/unit/test_daemon_lease.py
```
