# PR path manifest - creator-engine/ce-ops#518 - stale ticket reconciliation slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-518-stale-ticket-reconcile-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e6e5c4ec4f7e8c07920781b3134ef4e2ec7bc86abddd4bc359a75c40b2b8f13d

```text
.ce/changelog/ce-518-stale-ticket-reconcile-s1.md
.ce/pr-manifests/ce-518-stale-ticket-reconcile-s1.md
validators/creator_engine_validator/ticket_reconcile.py
validators/tests/unit/test_ticket_reconcile.py
```
