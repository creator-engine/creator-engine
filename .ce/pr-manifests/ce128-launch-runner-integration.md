# PR path manifest - ce128-launch-runner-integration

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-launch-runner-integration
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`137909c456d7adf57ccb24a6f9772e24d5b07bc0` (`ce128-launch-runner-integration-base`: current `origin/main` plus #389 and fixed #390 sibling heads).

- **Declared work class:** story

Scope:
ce-ops#128 SUB-C integration: compose backend-selected launch surfaces through
`RunnerBackend.provision -> run` and the existing visibility backend so
`ce launch --backend gvisor` and `ce lane launch --backend gvisor` run via the
Docker/runsc path without silently falling back to raw tmux.

Per-file purpose:
- **`.ce/changelog/ce128-launch-runner-integration.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-launch-runner-integration.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the visible runtime bridge as v1 launcher code.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - route runtime-policy lane launches through the bridge and record runner evidence in the ignored sidecar.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - route controller launches through the bridge and expose runner evidence in the launch result.
- **`validators/creator_engine_validator/runtime_backend_bridge.py`** *(A)* - visible composition bridge from gVisor `RunnerBackend` to `VisibilityBackend.ensure_surface`.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - controller launch success/fail-closed coverage for gVisor Docker/runsc rendering.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - lane launch success/fail-closed coverage for gVisor Docker/runsc rendering and sidecar evidence.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - expected v1 taxonomy count update.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=0c1d56b3d299d47849082e5109859fc99147e369dde8316aab5337036e465210

```text
.ce/changelog/ce128-launch-runner-integration.md
.ce/pr-manifests/ce128-launch-runner-integration.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/runtime_backend_bridge.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_version_boundary.py
```
