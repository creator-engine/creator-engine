# PR path manifest — creator-engine/ce-ops#410 · slice 9 ledger binding seam

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s9-ledger-binding-seam` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=3960d6bae5c2399e887440e619bf2277c9801094ff6fd7ae1ebb0c5ff1ce7462

```text
.ce/changelog/ce-410-s9-ledger-binding-seam.md
.ce/pr-manifests/ce-410-s9-ledger-binding-seam.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
