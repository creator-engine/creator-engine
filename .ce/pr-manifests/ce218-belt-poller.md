# PR path manifest — ce-ops#218 · integrator belt-poller (v1/v3-boundary-correct)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce218-belt-poller` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=2095f410aca6829aa1b6e1d0f7e2857e3bfb9b066754bfd2b7f611c7ba2ff7ab

```text
.ce/changelog/ce218-belt-poller.md
.ce/pr-manifests/ce218-belt-poller.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integration_queue_dry_run_contract.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_version_boundary.py
```
