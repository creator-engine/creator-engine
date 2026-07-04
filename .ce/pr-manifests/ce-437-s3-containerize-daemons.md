# PR path manifest — creator-engine/ce-ops#437 · containerize governance daemons + singleton-lease gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-437-s3-containerize-daemons` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=d879a2fb898c51bc3823ea41e5ad378a065a673b9287d9d35e416058c1c90dc0

```text
.ce/changelog/ce-437-s3-containerize-daemons.md
.ce/pr-manifests/ce-437-s3-containerize-daemons.md
deploy/daemons/Dockerfile
deploy/daemons/README.md
deploy/daemons/run-daemon-container.sh
deploy/queue-daemon/RELOCATION.md
deploy/queue-daemon/ce-queue-daemon.service
deploy/queue-daemon/launch-queue-daemon.sh
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/daemon_lease.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_daemon_lease.py
```
