# PR path manifest — ce-ops#615 · dispatch receipt schema + emit/verify slice 1

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=d7fb786dbea823cb7bae4aad47feaa808d15fa86784bad5da1d2942d9b2761a1

```text
.ce/changelog/ce-615-dispatch-receipts.md
.ce/pr-manifests/ce-615-dispatch-receipts.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_receipt.py
validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml
validators/tests/unit/test_dispatch_receipt.py
```
