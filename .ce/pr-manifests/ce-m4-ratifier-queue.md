# PR path manifest — ce-m4-ratifier-queue

This carrier lists the closed authorized path-set for the pure M4 ratifier
queue reducer.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2936e63d92aa80aef4c9f038248ee9e21b8bd4a55f059bb3c8c1b023b7129d96

```text
.ce/changelog/ce-m4-ratifier-queue.md
.ce/pr-manifests/ce-m4-ratifier-queue.md
validators/creator_engine_validator/forge/ratifier_queue.py
validators/tests/unit/test_ratifier_queue.py
```
