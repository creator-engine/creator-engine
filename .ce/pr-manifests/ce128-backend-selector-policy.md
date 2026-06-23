# PR path manifest - ce128-backend-selector-policy

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-backend-selector-policy
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`e75c9ab` (`origin/main` at branch creation).

- **Declared work class:** story

Scope:
ce-ops#128 SUB-A/SUB-D foundation: launch backend selector parsing, existing
runtime-policy backend resolution, launch-boundary policy stamping, and
fail-closed explicit backend refusal until RunnerBackend execution is wired.

Per-file purpose:
- **`.ce/changelog/ce128-backend-selector-policy.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-backend-selector-policy.md`** *(A)* - this closed path-set carrier.
- **`docs/contracts/runtime-policy.md`** *(M)* - document the `local-noop` policy backend and runtime resolver wording.
- **`schemas/runtime-policy.schema.yaml`** *(M)* - admit `local-noop` as a schema-valid backend.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - add `--backend` parser choices and pass-through for launch surfaces.
- **`validators/creator_engine_validator/checks/ce_runtime_policy.py`** *(M)* - add backend resolution and sanitized launch stamp helper.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - resolve/stamp runtime policies and fail closed for explicit backend lane launches.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - resolve/stamp runtime policies and fail closed for explicit backend controller launches.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - CLI selector parsing, stamp, and fail-closed coverage.
- **`validators/tests/unit/test_ce_runtime_policy.py`** *(M)* - schema/resolver/stamp coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=2555ed2d0ff9549526bc032bf483129998e676ed3487d6b5da5cd87285665abe

```text
.ce/changelog/ce128-backend-selector-policy.md
.ce/pr-manifests/ce128-backend-selector-policy.md
docs/contracts/runtime-policy.md
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/ce_runtime_policy.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_ce_runtime_policy.py
```
