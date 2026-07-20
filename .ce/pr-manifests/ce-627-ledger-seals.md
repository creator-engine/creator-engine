# PR path manifest — ce-ops#627 · hash-chained ledger seals

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-627-ledger-seals-dev4` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=434d0793f74aa6998c5adeb119e10842745c2eece198cf584cdc99bbadff4abd

```text
.ce/changelog/ce-627-ledger-seals.md
.ce/pr-manifests/ce-627-ledger-seals.md
validators/creator_engine_validator/side_effect_ledger_runtime.py
validators/tests/unit/test_side_effect_ledger_runtime.py
validators/tests/unit/test_validation_sandbox_runner.py
```
