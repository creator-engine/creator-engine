# PR path manifest — ce-ops#410 · slice 8a: shared container-launcher primitive

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s8a-shared-launcher` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=861aeb4550b31ffe040624b1f04f8bb1b9fa32166159c70137cf9ef51ba9f4c6

```text
.ce/changelog/ce-410-s8a-shared-launcher.md
.ce/pr-manifests/ce-410-s8a-shared-launcher.md
validators/creator_engine_validator/container_launcher.py
validators/creator_engine_validator/worker_runtime.py
validators/tests/unit/test_container_launcher.py
validators/tests/unit/test_worker_runtime.py
```
