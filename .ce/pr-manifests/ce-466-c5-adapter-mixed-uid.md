# PR path manifest — ce-ops#466 · Fix daemon container adapter reruns over production-owned state

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-466-c5-adapter-mixed-uid` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=22f885056cf787abaaf33e72c022c9b409ef6d678970d0b30813af95dba82995

```text
.ce/changelog/ce-466-c5-adapter-mixed-uid.md
.ce/pr-manifests/ce-466-c5-adapter-mixed-uid.md
deploy/daemons/README.md
deploy/daemons/run-daemon-container.sh
deploy/daemons/smoke-daemon-container.sh
validators/tests/unit/test_daemon_container_smoke.py
validators/tests/unit/test_daemon_lease.py
```
