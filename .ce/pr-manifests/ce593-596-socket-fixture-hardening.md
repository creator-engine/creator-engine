# PR path manifest — #593 and #596 · Harden unix socket fixture cleanup and annotation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce593-596-socket-fixture-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=908769d3e09a4b323bda0a2635de2754409e47330bff421084ae2c9cc0d7902c

```text
.ce/changelog/ce593-596-socket-fixture-hardening.md
.ce/pr-manifests/ce593-596-socket-fixture-hardening.md
validators/tests/conftest.py
validators/tests/unit/test_conftest_unix_socket_tmp_path.py
```
