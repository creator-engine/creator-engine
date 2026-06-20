# PR path manifest - ce109-ring1-fs-mediation - Ring-1 guard shim-root hardening

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce109-ring1-fs-mediation

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified BUILD MANDATE (ce-ops#109, latest comment) - Ring-1 Section-8c
filesystem mediation (Landlock credential-path read-deny). This follow-up keeps
the Section-8c implementation on current `origin/main` green while closing the
reviewed symlink-TOCTOU escape in the Ring-1 shim root allow-list path.

Base:
`707e440d8c4b04cb743498c63e94b80d7e513aee` (`origin/main` after #285).

The changes:
- Derive `DEFAULT_SHIM_DIR` under a process-scoped current-uid private parent
  (`/tmp/ce-ring1-tool-guard-<uid>-<pid>/shim`).
- Create and validate the shim root before Landlock setup: absolute path only,
  no symlink components, owner is current uid, no group/other mode bits,
  resolved path allow-listed, and resolved credential-shaped paths rejected.
- Harden the installer to create/validate a private shim parent and root, reject
  symlink shims, and write shim files through `O_EXCL` temp files before atomic
  replacement.
- Add unit and live Landlock regressions for the reviewed attack: a symlinked
  shim root pointing at an out-of-workspace private key is rejected before
  allow-listing, while a safe resolved shim root still denies the secret read.
- Keep OpenShell tests hermetic by pinning their default shim root under a
  per-test private parent.
- Rebuild the validator wheel and refresh `validators/wheelhouse/SHA256SUMS`.

Validation:
- `PYTHONPATH=validators /tmp/ce109-s8c-venv/bin/python -m pytest validators/tests/unit/test_runner_ring1_tool_guard.py validators/tests/unit/test_openshell_ring1_guard.py validators/tests/integration/test_fs_mediation_landlock.py -q` -> 30 passed.
- `cd validators/wheelhouse && sha256sum -c SHA256SUMS` -> all OK.
- `verify_wheel_matches_source(Path.cwd())` -> PASS.
- `registered_checks()` -> 55.
- Landlock ABI on this host: 8.

Wheel:
`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`
sha256 = `a47466ed1e1035e2e68ae7fbc807f50c5ad51ecf7d9cc3d963e1c164838f2a66`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=0a1945092c8c4d4045c80c769a35138494eb270c9b3df6867c419eae69b7d141

```text
.ce/changelog/ce109-ring1-fs-mediation.md
.ce/pr-manifests/ce109-ring1-fs-mediation.md
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/integration/test_fs_mediation_landlock.py
validators/tests/unit/test_openshell_ring1_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
