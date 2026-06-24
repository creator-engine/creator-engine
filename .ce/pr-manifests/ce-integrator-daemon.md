# PR path manifest — ce-ops#218 · Integrator belt daemon — autonomous fail-closed merge

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-integrator-daemon` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=4c9583ded059da86ebf18d8e4e59bbb6bc2e475fedd0bdf08ea12526accf1ba2

```text
.ce/changelog/ce-integrator-daemon.md
.ce/pr-manifests/ce-integrator-daemon.md
docs/operations/INTEGRATOR_BELT_DAEMON.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
```
