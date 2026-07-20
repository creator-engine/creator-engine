# PR path manifest — ce-ops#615 · dispatch receipt schema + emit/verify slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-615-rebase-staging` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=01d19850141088b474fe4e3eaf1af4e73c3608146834686d45373af396f298ab

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-615-rebase-staging.md
.ce/pr-manifests/ce-615-rebase-staging.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_receipt.py
validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_dispatch_receipt.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
