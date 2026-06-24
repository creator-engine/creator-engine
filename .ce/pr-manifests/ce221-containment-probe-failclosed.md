# PR path manifest — ce-ops#221 · containment probed + fail-closed launch

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce221-containment-probe-failclosed` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=8e41386464e1ed3c9bce18f7dcb45c882e4ef18aa5e9b92735441d088215fd42

```text
.ce/changelog/ce221-containment-probe-failclosed.md
.ce/pr-manifests/ce221-containment-probe-failclosed.md
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/runtime_backend_bridge.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_contained_launch_proof.py
validators/tests/unit/test_lane_runtime.py
```
