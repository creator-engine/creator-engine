# PR path manifest — ce-ops#410 · Daemon path allocation core

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-alloc-core` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=bd34b8581ec4c0aab00582b3d5aa97e0cbd8f3929df3cb5d4b2a282a920cf708

```text
.ce/changelog/ce-410-alloc-core.md
.ce/pr-manifests/ce-410-alloc-core.md
validators/creator_engine_validator/forge/daemon_allocation.py
validators/tests/unit/test_daemon_allocation.py
```
