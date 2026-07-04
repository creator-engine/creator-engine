# PR path manifest — ce-ops#422 · Add tenant record schema and validator

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-422-tenant-record-schema` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=1d1be21fce524cfea034ca8cda843ee9996f2a83ae650ce1136d824b77b93186

```text
.ce/changelog/ce-422-tenant-record-schema.md
.ce/pr-manifests/ce-422-tenant-record-schema.md
.ce/reference/schemas.generated.md
examples/well-formed/tenant-records/acme.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/tenant_record.py
validators/creator_engine_validator/schemas/tenant-record.schema.yaml
validators/tests/unit/test_tenant_record.py
```
