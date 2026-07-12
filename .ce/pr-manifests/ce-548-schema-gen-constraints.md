# PR path manifest — ce-ops#548 · Render direct schema numeric constraints

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-548-schema-gen-constraints` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=927e05caa5112876207dffa16b15fcefe50dbc59ba906be2dc49ff45c66161c8

```text
.ce/changelog/ce-548-schema-gen-constraints.md
.ce/pr-manifests/ce-548-schema-gen-constraints.md
.ce/reference/schemas.generated.md
scripts/gen_schema_reference.py
validators/tests/unit/test_schema_reference_autogen_sync.py
```
