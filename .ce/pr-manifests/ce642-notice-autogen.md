# PR path manifest — ce-ops#642 NOTICE inventory autogen

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly this set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

Scope: generate the marked third-party package/version inventories in `NOTICE`:
the lock's ordinary runtime closure and the dev requirements verified against
vendored development wheels. Add a fail-closed sync guard that rides the
existing validator check registry and prove stale-NOTICE, wheel-mismatch,
runtime-extra exclusion, and curated-attribution preservation. License
attribution remains curated because `uv.lock` does not carry authoritative
license terms.

Per-file purpose:

- **`.ce/changelog/ce642-notice-autogen.md`** *(A)* — change record.
- **`.ce/pr-manifests/ce642-notice-autogen.md`** *(A)* — this closed carrier.
- **`NOTICE`** *(M)* — marked generated runtime/dev inventories and the
  hand-maintained per-package license-attribution section.
- **`scripts/gen_notice_inventory.py`** *(A)* — deterministic inventory
  generator with read-only `--check` and scoped `--write` modes.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* — registers
  the existing-gate sync guard.
- **`validators/creator_engine_validator/checks/notice_inventory_autogen_sync.py`** *(A)* — fail-closed stale/unreadable inventory guard.
- **`validators/tests/unit/test_notice_inventory_autogen_sync.py`** *(A)* —
  focused fresh, stale-NOTICE, stale-lock, and write/check tests.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=e2e75976cbbfed398514f9f7b70c20611827a2320e5455735515a887e9878588

```text
.ce/changelog/ce642-notice-autogen.md
.ce/pr-manifests/ce642-notice-autogen.md
NOTICE
scripts/gen_notice_inventory.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/notice_inventory_autogen_sync.py
validators/tests/unit/test_notice_inventory_autogen_sync.py
```
