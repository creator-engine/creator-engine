# PR path manifest - ce109-ring1-fs-mediation - Ring-1 guard shim path isolation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce109-ring1-fs-mediation

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified BUILD MANDATE (ce-ops#109, latest comment) - Ring-1 Section-8c
filesystem mediation (Landlock credential-path read-deny). This follow-up keeps
the already-merged Section-8c implementation on current `origin/main` green on
multi-seat and parallel-test hosts by removing the shared default `/tmp` shim
collision observed in the runner integration.

Base:
`707e440d8c4b04cb743498c63e94b80d7e513aee` (`origin/main` after #285).

The changes:
- Derive `DEFAULT_SHIM_DIR` from the current uid and process id, changing the
  default from the legacy shared `/tmp/ce-ring1-tool-guard` to a process-scoped
  path such as `/tmp/ce-ring1-tool-guard-<uid>-<pid>`.
- Preserve every explicit `shim_dir` call site and the existing PATH/env shape.
- Add a unit ratchet that the default shim directory is process-scoped.
- Rebuild the validator wheel and refresh `validators/wheelhouse/SHA256SUMS`.

Validation:
- `PYTHONPATH=validators /tmp/ce109-s8c-venv/bin/python -m pytest validators/tests/unit/test_runner_ring1_tool_guard.py -q` -> 14 passed.
- `PYTHONPATH=validators /tmp/ce109-s8c-venv/bin/python -m pytest validators/tests -q -n auto --dist loadgroup` -> 3571 passed, 7 skipped.
- `cd validators/wheelhouse && sha256sum -c SHA256SUMS` -> all OK.
- Offline install from `validators/wheelhouse` -> succeeded.
- `registered_checks()` -> 55.
- Landlock ABI on this host: 8.

Wheel:
`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`
sha256 = `98186ddabe75442d01819e13a4d43aeeb9a02e566c65e83d892d17ce9a5b0738`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=0732eb2605eaa470d6052f471d1918d5e90e43b528e019c23592f3d54dd1b07c

```text
.ce/changelog/ce109-ring1-fs-mediation.md
.ce/pr-manifests/ce109-ring1-fs-mediation.md
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
