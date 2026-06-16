# PR path manifest - ga2-runner-ring1-impl

Design/task: Runner-owned Ring-1 increment 1 per
`DESIGN_CE_RUNNER_RING1_20260616.md`.

Base:
`bcf84649ab6343784bd1aa45690f32ded21ba339`

This is the closed path set for the PATH-shim proof only. It intentionally does
not claim hardened Ring-1 coverage for absolute binary paths, bundled clients,
libgit2/JGit, direct HTTPS API writes, PATH resets, environment/posture reset
(e.g. `CE_RING1_POSTURE`), or arbitrary filesystem syscalls.

Per-file purpose:

- **`.ce/changelog/ga2-runner-ring1-impl.md`** *(A)* - changelog fragment with precise coverage and gap language.
- **`.ce/pr-manifests/ga2-runner-ring1-impl.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the new guard module as v3 runner runtime.
- **`validators/creator_engine_validator/runner/__init__.py`** *(M)* - export guard config/runtime helpers for runner tests and wiring.
- **`validators/creator_engine_validator/runner/openshell_backend.py`** *(M)* - opt-in guard install after sandbox create and guarded PATH injection during run.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(A)* - render POSIX git/gh shims that call hook-check and fail closed on deny/block or CLI failure.
- **`validators/tests/integration/test_runner_ring1_codex_push.py`** *(A)* - fake-codex child-process proof that governed `git push` is denied before real git.
- **`validators/tests/unit/test_openshell_ring1_guard.py`** *(A)* - OpenShell guard lifecycle and validation-order unit tests.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(A)* - shim rendering, event mapping, decision parsing, and fail-closed unit tests.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - count/classification update plus AST canary that the guard imports no v1 `hook_check`.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=c30433864388ff2d8c1e31165ab38b03dfcc02759e298850c8f1f852c64ad4ee

```text
.ce/changelog/ga2-runner-ring1-impl.md
.ce/pr-manifests/ga2-runner-ring1-impl.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/unit/test_openshell_ring1_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
