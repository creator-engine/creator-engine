# PR path manifest - ce173-idempotent-reinstall

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce173-idempotent-reinstall
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#173 idempotent / overwrite-safe re-install, the Release & Update
foundation for epic ce-ops#191.

Per-file purpose:
- **`.ce/changelog/ce173-idempotent-reinstall.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce173-idempotent-reinstall.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure reinstall convergence planners for scaffold, venv, App config, token, partial-run, and artifact verification decisions.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - shell bootstrap regression for partial/corrupt venv repair without manual teardown.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - prior-state, artifact-verification, and fail-closed planner coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b3e5e4186da13ab2773415560191573219dae03f8c340fe483975bf38db51479

```text
.ce/changelog/ce173-idempotent-reinstall.md
.ce/pr-manifests/ce173-idempotent-reinstall.md
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_v3_installer.py
```
