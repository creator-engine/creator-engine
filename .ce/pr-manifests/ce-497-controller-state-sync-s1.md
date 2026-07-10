# PR path manifest — ce-497 · Add controller state snapshot tool

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-497-controller-state-sync-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=dec7260d1de387235b78656b808ac2df0c03c8b46729d91e2821920f2be1919c

```text
.ce/changelog/ce-497-controller-state-sync-s1.md
.ce/pr-manifests/ce-497-controller-state-sync-s1.md
tools/controller/state_sync.py
validators/tests/unit/test_controller_state_sync.py
```
