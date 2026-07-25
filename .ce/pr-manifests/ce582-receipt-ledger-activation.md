# PR path manifest — conveyor receipt-ledger activation

This carrier lists the closed authorized path set for the explicit legacy
receipt migration, its no-reentry proof, and its Operator runbook.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=23b6589ffb2fd2fe569d4e48fbf57f2b08b4dc88d320bb1e45f0e120dfea8421

```text
.ce/changelog/ce582-receipt-ledger-activation.md
.ce/pr-manifests/ce582-receipt-ledger-activation.md
playbooks/controller/runbooks/conveyor-receipt-ledger-activation.md
validators/creator_engine_validator/conveyor_discovery.py
validators/creator_engine_validator/conveyor_receipt_activation.py
validators/tests/unit/test_conveyor_receipt_activation.py
```
