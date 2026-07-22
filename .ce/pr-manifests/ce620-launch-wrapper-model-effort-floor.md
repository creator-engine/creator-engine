# PR path manifest — ce-ops#620 · Launch-wrapper model/effort floor

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce620-launch-wrapper-model-effort-floor`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=27

AUTHORIZED_PATHS_SHA256=1f60c0ba15b9fc4c03223e1a1faf36b56db4a35d9b8f07448353df69c86363da

```text
.ce/changelog/ce620-launch-wrapper-model-effort-floor.md
.ce/pr-manifests/ce620-launch-wrapper-model-effort-floor.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
playbooks/controller/MODEL_ROUTING_GPT56_RATIFIED_20260710.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/claude_launch_spec.py
validators/creator_engine_validator/codex_launch_spec.py
validators/creator_engine_validator/dispatch_receipt.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/model_effort_policy.py
validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml
validators/creator_engine_validator/worker_spawn.py
validators/tests/integration/test_ce_launch_cli.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_claude_launch_spec.py
validators/tests/unit/test_codex_launch_spec.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_dispatch_receipt.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_vps_runsc_launcher.py
validators/tests/unit/test_worker_spawn.py
```
