# PR path manifest — ce-ops#615 · dispatch receipt schema + emit/verify slice 1

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=e19b6a955a06b3895bb35938dd0961169e67cfb27213dbfe827b7eb5cb1ea6ce

```text
.ce/changelog/ce-615-dispatch-receipts.md
.ce/pr-manifests/ce-615-dispatch-receipts.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_receipt.py
validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml
validators/tests/unit/test_dispatch_receipt.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
