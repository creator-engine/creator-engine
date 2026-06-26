# PR path manifest — ce-ops#221 · Probe contained launch with launch-owned gVisor proof

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce221-probed-containment-v2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=d1ff13544a961a47a6c3110c49dae7821aa961e67cefd20d67a0fb6bb8f52387

```text
.ce/changelog/ce221-probed-containment-v2.md
.ce/pr-manifests/ce221-probed-containment-v2.md
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runtime_backend_bridge.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_contained_launch_proof.py
validators/tests/unit/test_gvisor_proxy_backend.py
validators/tests/unit/test_lane_runtime.py
```
