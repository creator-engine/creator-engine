# PR path manifest — creator-engine/ce-ops#423 · Tenant denylist matrix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-423-tenant-denylist-matrix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a3cfb2852224d602b66a83f87f400451172b20617f61f1bed50a8ba7396ba91c

```text
.ce/changelog/ce-423-tenant-denylist-matrix.md
.ce/pr-manifests/ce-423-tenant-denylist-matrix.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/tenant_confidentiality.py
validators/tests/unit/test_tenant_confidentiality.py
```
