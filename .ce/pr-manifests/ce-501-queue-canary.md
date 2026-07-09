# PR path manifest — ce-501-queue-canary

slug: ce-501-queue-canary

This per-PR carrier lists the closed authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-501-queue-canary`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=3c0270d2e4865f0387badce376cc8f01c07e44929fce59c45339f22310a90094

```text
.ce/changelog/ce-501-queue-canary.md
.ce/pr-manifests/ce-501-queue-canary.md
deploy/queue-daemon/launch-queue-daemon.sh
validators/tests/unit/test_queue_daemon_canary_launch.py
```
