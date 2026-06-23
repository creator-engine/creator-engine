# PR path manifest - ce216-integrator-runner

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce216-integrator-runner
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch handoff.

- **Declared work class:** story

Scope:
ce-ops#216 Unit 5. Add the one-shot Integrator MVP runner that wires the landed
eviction detector, deterministic resolvers, Unit 3 executor API, and escalation
seam. No always-on daemon and no direct merge bypass is introduced.

Per-file purpose:
- **`.ce/changelog/ce216-integrator-runner.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce216-integrator-runner.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the runner as v3 forge code.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* - expose runner carrier/result APIs through the forge package surface.
- **`validators/creator_engine_validator/forge/integrator_runner.py`** *(A)* - one-shot Integrator MVP runner implementation.
- **`validators/creator_engine_validator/integration_queue_dry_run.py`** *(M)* - fail-closed injectable live-action seam for queue dry-run requests.
- **`validators/tests/unit/test_integrator_runner.py`** *(A)* - poll/detect/resolve/execute, semantic escalation, and gate-refusal coverage.
- **`validators/tests/unit/test_integration_queue_dry_run_contract.py`** *(M)* - live-action callback acceptance/refusal coverage.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update the v3 module count and classification assertion.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=57cf55a4fb395fa68e4c00e483595d132daf370f0f6ec452a5c34d3194fcaf64

```text
.ce/changelog/ce216-integrator-runner.md
.ce/pr-manifests/ce216-integrator-runner.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/integrator_runner.py
validators/creator_engine_validator/integration_queue_dry_run.py
validators/tests/unit/test_integrator_runner.py
validators/tests/unit/test_integration_queue_dry_run_contract.py
validators/tests/unit/test_version_boundary.py
```
