# PR path manifest - ce147-identity-registry-dimensions

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce147-identity-registry-dimensions --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#147 identity-registry schema expansion, limited to items 1-5. Public
artifact values remain redacted placeholders only; no authoritative fleet
identity values are introduced here.

Per-file purpose (closed path-set - 5 paths):
- **`.ce/changelog/ce147-identity-registry-dimensions.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce147-identity-registry-dimensions.md`** *(A)* - this carrier.
- **`docs/governance/identity-registry.example.yaml`** *(M)* - redacted schema-conformance examples for new fields and arrays.
- **`schemas/identity-registry.schema.yaml`** *(M)* - repo inventory, account, token, OpenBao, and host topology schema dimensions.
- **`validators/tests/unit/test_identity_registry_schema.py`** *(A)* - focused pytest coverage for valid and malformed expanded registry documents.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=27b815acef3a29cfd0347191004fb811fab7a0dbf2af820e379570cd0e9d0a04

```text
.ce/changelog/ce147-identity-registry-dimensions.md
.ce/pr-manifests/ce147-identity-registry-dimensions.md
docs/governance/identity-registry.example.yaml
schemas/identity-registry.schema.yaml
validators/tests/unit/test_identity_registry_schema.py
```
