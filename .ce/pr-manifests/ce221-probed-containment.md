# PR path manifest — ce-ops#221 · require probed containment proof

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce221-probed-containment` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=b9f35e94c2e61c0b032c57223e4d9eb321f9618b741e8633ca08922c694d2ac5

```text
.ce/changelog/ce221-probed-containment.md
.ce/pr-manifests/ce221-probed-containment.md
validators/creator_engine_validator/containment_probe.py
validators/creator_engine_validator/containment_status.py
validators/creator_engine_validator/runner/backend.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/creator_engine_validator/runtime_backend_bridge.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_contained_launch_proof.py
validators/tests/unit/test_containment_probe.py
validators/tests/unit/test_containment_status.py
```
