# PR path manifest — ce-ops#645 · Cover AF_UNIX fixture symlink cleanup

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce645-fixture-followups` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=ccac29d4c34e944e6708e7125951a5a0cbdcf0935df305b3219c21f0d6241288

```text
.ce/changelog/ce645-fixture-followups.md
.ce/pr-manifests/ce645-fixture-followups.md
validators/tests/unit/test_conftest_unix_socket_tmp_path.py
```
