# PR path manifest - ga2-runner-ring1-impl

Design/task: Runner-owned Ring-1 increment 1 per
`DESIGN_CE_RUNNER_RING1_20260616.md`.

Base:
`dd46b64597c29fe482384a04b8d56984c503c623`

This is the closed path set for the PATH-shim proof only. It intentionally does
not claim hardened Ring-1 coverage for absolute binary paths, bundled clients,
libgit2/JGit, direct HTTPS API writes, PATH resets, environment/posture reset
(e.g. `CE_RING1_POSTURE`), or arbitrary filesystem syscalls.

Per-file purpose:

- **`.ce/changelog/ga2-runner-ring1-impl.md`** *(A)* - changelog fragment with precise coverage and gap language.
- **`.ce/pr-manifests/ga2-runner-ring1-impl.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify the new guard module as v3 runner runtime.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - parse git global options and inline aliases before classifying deploy mechanics; closes ce-ops#104.
- **`validators/creator_engine_validator/runner/__init__.py`** *(M)* - export guard config/runtime helpers for runner tests and wiring.
- **`validators/creator_engine_validator/runner/openshell_backend.py`** *(M)* - opt-in guard install after sandbox create and guarded PATH injection during run.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(A)* - render POSIX git/gh shims that call hook-check and fail closed on deny/block or CLI failure.
- **`validators/tests/integration/test_runner_ring1_codex_push.py`** *(A)* - fake-codex child-process proof that governed `git push` is denied before real git.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - shared classifier canaries for git global options, inline aliases, plain push, and safe status.
- **`validators/tests/unit/test_openshell_ring1_guard.py`** *(A)* - OpenShell guard lifecycle and validation-order unit tests.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(A)* - shim rendering, event mapping, decision parsing, and fail-closed unit tests.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - count/classification update plus AST canary that the guard imports no v1 `hook_check`.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=1243aa03108acf1faa0225713035a61a85415ed8825a53bec0e99455019e1aef

```text
.ce/changelog/ga2-runner-ring1-impl.md
.ce/pr-manifests/ga2-runner-ring1-impl.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_openshell_ring1_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
