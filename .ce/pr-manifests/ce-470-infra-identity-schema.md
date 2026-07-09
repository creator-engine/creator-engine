# ce-470-infra-identity-schema

- **Declared work class:** S

This per-PR carrier lists the closed authorized path-set for this PR. The
carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=590b566943de4c93b986cd8117c61d166de5186b9aec5f2a80e8bc8f9aa280fb

```text
.ce/changelog/ce-470-infra-identity-schema.md
.ce/pr-manifests/ce-470-infra-identity-schema.md
docs/governance/identity-registry.example.yaml
validators/creator_engine_validator/schemas/identity-registry.schema.yaml
validators/tests/unit/test_identity_registry_schema.py
```

CLI recall path (`ce identity lookup`) is deferred to a follow-on unit after the frozen CLI territory is available.
