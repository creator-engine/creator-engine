# PR path manifest - ce-fleet-status

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-fleet-status` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=2c27937d77aa84c07c0979c560e3b1138f8d5b9be27eb742290f4edd3ada5399

```text
.ce/changelog/ce-fleet-status.md
.ce/pr-manifests/ce-fleet-status.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/fleet_status.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_fleet_status.py
validators/tests/unit/test_version_boundary.py
```
