# PR path manifest - ce-518s2-reconcile-feed

slug: ce-518s2-reconcile-feed

This carrier lists the closed authorized path-set for the reconcile feed slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=22d8abc0b188c1ba0ff1492e9169dab80bb5b2f5660b29449baf178abd3fb047

```text
.ce/changelog/ce-518s2-reconcile-feed.md
.ce/pr-manifests/ce-518s2-reconcile-feed.md
validators/creator_engine_validator/ticket_reconcile_feed.py
validators/tests/unit/test_ticket_reconcile_feed.py
```
