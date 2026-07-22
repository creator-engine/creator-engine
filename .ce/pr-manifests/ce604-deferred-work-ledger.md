# PR path manifest — ce-ops#604 · Deferred-work ledger read-back ratchet

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce604-deferred-work-ledger` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=23c0f68d5490b3583766c99c3b286579ab175d14faedcdf324fdf34bce429b42

```text
.ce/changelog/ce604-deferred-work-ledger.md
.ce/deferred/ledger.yaml
.ce/pr-manifests/ce604-deferred-work-ledger.md
.ce/reference/schemas.generated.md
docs/design/deferred-work-ledger.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/deferred_work_ledger.py
validators/creator_engine_validator/schemas/deferred-work-ledger.schema.yaml
validators/tests/unit/test_deferred_work_ledger.py
```
