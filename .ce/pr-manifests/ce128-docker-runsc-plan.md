# PR path manifest - ce128-docker-runsc-plan

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-docker-runsc-plan
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch creation.

- **Declared work class:** story

Scope:
ce-ops#128 SUB-B. Render the gVisor backend plan as the DGX Docker
`runsc-gvproxy-ptrace` invocation, preserving this as a rendering/provisioning
slice without threading launch/lane execution.

Per-file purpose:
- **`.ce/changelog/ce128-docker-runsc-plan.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-docker-runsc-plan.md`** *(A)* - this closed path-set carrier.
- **`deploy/dgx-runsc/README.md`** *(M)* - update the local runner evidence to the Docker runsc plan shape.
- **`validators/creator_engine_validator/runner/__init__.py`** *(M)* - export the new `RunscPlanRejected` API.
- **`validators/creator_engine_validator/runner/gvisor_proxy_backend.py`** *(M)* - render and validate Docker `runsc-gvproxy-ptrace` plans.
- **`validators/tests/unit/test_gvisor_proxy_backend.py`** *(M)* - cover Docker argv rendering and fail-closed input validation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=6116ce61d9b965538264a02603123b26ffec1e8e171d59d0bbb744e2a76d458e

```text
.ce/changelog/ce128-docker-runsc-plan.md
.ce/pr-manifests/ce128-docker-runsc-plan.md
deploy/dgx-runsc/README.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/tests/unit/test_gvisor_proxy_backend.py
```
