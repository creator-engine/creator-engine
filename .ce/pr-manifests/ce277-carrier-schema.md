# PR path manifest — ce-ops#277 · surface-bump carrier schema + runbook + validator check

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce277-carrier-schema` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5b132997a01195a58dc1cb729ac5a8d392453c18d4a77c901aea2f04941f8984

```text
.ce/changelog/ce277-carrier-schema.md
.ce/pr-manifests/ce277-carrier-schema.md
carriers/surface-bump-TEMPLATE.md
docs/SURFACE_UPDATE_RUNBOOK.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_bump_has_carrier.py
```
