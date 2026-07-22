# PR path manifest — ce-ops#594 · Bound stale-ticket reconciliation subprocesses

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce594-reconcile-timeouts` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=7b8dc5ddc2f4c729c0d2990de734f69bdeb7fe19f383edab9cada3af5fd990a5

```text
.ce/changelog/ce594-reconcile-timeouts.md
.ce/pr-manifests/ce594-reconcile-timeouts.md
.github/workflows/ce-ops-stale-ticket-reconcile.yml
validators/creator_engine_validator/ticket_reconcile_feed.py
validators/tests/unit/test_ticket_reconcile_feed.py
```
