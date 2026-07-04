# PR path manifest — ce-ops#388 · conveyor seat discovery runner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-conveyor-discovery` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=47c161379f3e94a28118f9a3f5067a04bc4a26d4db6227536d58b7bded1e00e1

```text
.ce/changelog/ce-388-conveyor-discovery.md
.ce/pr-manifests/ce-388-conveyor-discovery.md
validators/creator_engine_validator/conveyor_discovery.py
validators/tests/unit/test_conveyor_discovery.py
```
