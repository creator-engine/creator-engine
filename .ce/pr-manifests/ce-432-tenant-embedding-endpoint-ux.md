# PR path manifest — ce-ops#432 · surface launch recall status

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-432-tenant-embedding-endpoint-ux` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=656347b2902704b81ab778b1dabd8f7d9667088748e8c8466a20c2a7b950702f

```text
.ce/changelog/ce-432-tenant-embedding-endpoint-ux.md
.ce/pr-manifests/ce-432-tenant-embedding-endpoint-ux.md
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_launch_runtime.py
```
