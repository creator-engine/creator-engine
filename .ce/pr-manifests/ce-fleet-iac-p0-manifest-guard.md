# PR path manifest — Fleet-IaC P0 · Fleet manifest schema and internal identifier guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-fleet-iac-p0-manifest-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=c97d6496cfd4c43952463d18ac929114bff6aca74b9bfde808990595b617945e

```text
.ce/changelog/ce-fleet-iac-p0-manifest-guard.md
.ce/pr-manifests/ce-fleet-iac-p0-manifest-guard.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/fleet_manifest_guard.py
validators/creator_engine_validator/fleet_manifest.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/schemas/fleet-manifest.schema.yaml
validators/tests/unit/test_fleet_manifest_guard.py
validators/tests/unit/test_pr_preflight.py
```
