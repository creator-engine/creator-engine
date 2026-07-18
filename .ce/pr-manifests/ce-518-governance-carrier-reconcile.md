# PR path manifest - ce-518-governance-carrier-reconcile

slug: ce-518-governance-carrier-reconcile

This carrier lists the closed authorized path-set for the complete stale-ticket
reconciliation advisory.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=464bbef95e0fee996203151d6aac7b89af7e8a25202c77981db262d3b62709f7

```text
.ce/changelog/ce-518-governance-carrier-reconcile.md
.ce/pr-manifests/ce-518-governance-carrier-reconcile.md
.github/workflows/ce-ops-stale-ticket-reconcile.yml
validators/creator_engine_validator/ticket_reconcile.py
validators/creator_engine_validator/ticket_reconcile_feed.py
validators/tests/unit/test_ticket_reconcile.py
validators/tests/unit/test_ticket_reconcile_feed.py
```
