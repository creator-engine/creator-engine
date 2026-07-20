# PR path manifest — ce-ops#627 · hash-chained ledger seals

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-627-ledger-seals-dev4` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a442237996dee0969371b46f75463ecd36d58a4c87dc7dc42fff676dd90951f3

```text
.ce/changelog/ce-627-ledger-seals-dev4.md
.ce/pr-manifests/ce-627-ledger-seals-dev4.md
validators/creator_engine_validator/side_effect_ledger_runtime.py
validators/tests/unit/test_side_effect_ledger_runtime.py
validators/tests/unit/test_validation_sandbox_runner.py
```
