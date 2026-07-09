# PR path manifest — ce-501-queue-canary

slug: ce-501-queue-canary

This per-PR carrier lists the closed authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-501-queue-canary`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=e755059755890e52b95998acda4e2688714532d4cd4320083deddbe70bc3103d

```text
.ce/changelog/ce-501-queue-canary.md
.ce/pr-manifests/ce-501-queue-canary.md
.ce/wt-ce501/READY
deploy/queue-daemon/launch-queue-daemon.sh
validators/tests/unit/test_queue_daemon_canary_launch.py
```
