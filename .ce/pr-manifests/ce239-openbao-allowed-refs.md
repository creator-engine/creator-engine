# PR path manifest — ce-ops#239 · harden prod openbao backend allowed_refs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce239-openbao-allowed-refs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d0aa335ac046f8617dcd413926c5ba6b9a9329868e5887e69fc89bca1e08b51c

```text
.ce/changelog/ce239-openbao-allowed-refs.md
.ce/pr-manifests/ce239-openbao-allowed-refs.md
validators/creator_engine_validator/secret_identity.py
validators/tests/unit/test_secret_identity.py
```
