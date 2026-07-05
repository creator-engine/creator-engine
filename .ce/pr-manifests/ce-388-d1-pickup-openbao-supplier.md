# PR path manifest — ce-388 · review-pickup OpenBao token supplier

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-388-d1-pickup-openbao-supplier`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

- **Declared work class:** story

Scope: ce-388 D1 review-pickup token wiring. Add SecretIdentity/OpenBao-backed
pickup-token supply without changing the unconfigured static-token path.

Per-file purpose:
- **`.ce/changelog/ce-388-d1-pickup-openbao-supplier.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-388-d1-pickup-openbao-supplier.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/secret_identity.py`** *(M)* - review-pickup token SecretRef defaults.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - pickup-token secret flags and supplier construction.
- **`validators/creator_engine_validator/forge/review_pickup.py`** *(M)* - per-pass supplier refresh and bounded retry.
- **`validators/tests/unit/test_review_pickup_openbao_supplier.py`** *(A)* - minimal offline smoke coverage for the touched-module coupling.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=e9aad98ba58c913aaf30852d9f9e5e8251c22c90aff90aae92ec0acafcd18e00

```text
.ce/changelog/ce-388-d1-pickup-openbao-supplier.md
.ce/pr-manifests/ce-388-d1-pickup-openbao-supplier.md
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/secret_identity.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_pickup_openbao_supplier.py
```
