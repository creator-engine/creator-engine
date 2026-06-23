# PR path manifest - ce197-launcher-refuse

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce197-launcher-refuse
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`a83d384d` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#197 PR-6 / ce-ops#212 launcher resolve-harness refusal and lifecycle
reconciliation for Codex exec-fail seats.

Per-file purpose:
- **`.ce/changelog/ce197-launcher-refuse.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce197-launcher-refuse.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/codex_launch_spec.py`** *(M)* - Codex harness resolver and absolute-path governed command.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - pre-spawn Codex resolver refusal, resume no-spawn return, sentinel reuse refusal, and post-registration reconcile.
- **`validators/creator_engine_validator/seat_lifecycle.py`** *(M)* - idempotent sentinel-exit lifecycle reconciliation helper.
- **`validators/tests/integration/test_ce_launch_cli.py`** *(M)* - fake Codex path expectation for dry-run integration coverage.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - fake Codex path expectation for CLI dry-run coverage.
- **`validators/tests/unit/test_codex_launch_spec.py`** *(M)* - resolver and absolute-path governed-command unit coverage.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* - pre-side-effect refusal, no-spawn resume, sentinel reuse refusal, and exit-127 reconcile coverage.
- **`validators/tests/unit/test_launch_runtime_resource_bound.py`** *(M)* - resource-bound dry-run expectation for absolute Codex harness path.
- **`validators/tests/unit/test_seat_lifecycle.py`** *(A)* - lifecycle reconciliation unit coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=15f4572a8c3a3fe3e0206d3474c82a5593318147ff7ac066764b66b665e27776

```text
.ce/changelog/ce197-launcher-refuse.md
.ce/pr-manifests/ce197-launcher-refuse.md
validators/creator_engine_validator/codex_launch_spec.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/seat_lifecycle.py
validators/tests/integration/test_ce_launch_cli.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_codex_launch_spec.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_seat_lifecycle.py
```
