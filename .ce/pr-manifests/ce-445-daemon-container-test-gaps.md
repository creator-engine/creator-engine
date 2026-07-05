# PR path manifest — ce-ops#445 · daemon container env-file/cacert refusal tests and conveyor invocation pin

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-445-daemon-container-test-gaps` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=4439d911e040630c60b82fc679a5b38531b8e26fec35ee366180372ba80ca9bc

```text
.ce/changelog/ce-445-daemon-container-test-gaps.md
.ce/pr-manifests/ce-445-daemon-container-test-gaps.md
validators/tests/unit/test_daemon_lease.py
```
