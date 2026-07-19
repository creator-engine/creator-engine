# PR path manifest — ce-ops#615 · dispatch receipt schema + emit/verify slice 1

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=23669643a428867f7b30d4f754c7e7b5eb021ab7c0cfa1c1f64b20621d5472f0

```text
.ce/changelog/ce-615-dispatch-receipts.md
.ce/pr-manifests/ce-615-dispatch-receipts.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_receipt.py
validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml
validators/tests/unit/test_dispatch_receipt.py
```
