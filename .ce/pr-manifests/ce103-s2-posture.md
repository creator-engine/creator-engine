# PR path manifest - ce103-s2-posture - Ring-1 posture non-spoofability

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce103-s2-posture

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified mandate `/home/nefarious/Documents/MANDATE_s2_posture_build.md`,
Ring-1 Section-8 S2 posture non-spoofability. Build seat commits locally and
holds; no push, PR, or issue mutation.

Base:
`54b3c737a9f0bacb1a49dae56dc5247e5689806f` (`origin/main` at branch creation).

The changes (ce-ops#103 Scope-2 S2):
- Runner `Ring1ToolGuardConfig` now has a `posture="governed"` hard floor. The
  generated shim bakes `--posture governed` into its 0555 script text and does
  not consult `CE_RING1_POSTURE` or `CE_LEDGER_ROOT` from child environment for
  that decision.
- Optional posture/ledger roots are rendered as immutable shim constants. The
  OpenShell backend's default guard derives the runtime worktree root from the
  provisioning policy and bakes its Active-Work Ledger root by default.
- The deployed-Claude `--posture auto` path is unchanged.
- Tests cover both directions: env-spoofed `git push` remains denied with exit
  121, and governed `git status` remains allowed.
- The validator app wheel is rebuilt from the current source and
  `validators/wheelhouse/SHA256SUMS` is refreshed. New app-wheel digest:
  `9ab4107e7667e324c75bfee2e30eca31d39998cd8563abf180ae134313b87cfc`.

Per-file purpose (the closed path-set - 11 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce103-s2-posture.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce103-s2-posture.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/runner/openshell_backend.py`** *(M)* -
  default Ring-1 guard provisioning with baked posture/ledger roots.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* -
  governed posture hard floor and immutable shim posture/root constants.
- **`validators/tests/integration/test_runner_ring1_codex_push.py`** *(M)* -
  env-spoof deny proof and governed status allow regression.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - runner explicit
  governed override regression.
- **`validators/tests/unit/test_openshell_backend.py`** *(M)* - default guard
  install accounting for lifecycle tests.
- **`validators/tests/unit/test_openshell_ring1_guard.py`** *(M)* - OpenShell
  default guard/root provisioning coverage.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(M)* - shim
  immutability, env injection, and hard-floor unit coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - rebuilt-wheel digest.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* -
  rebuilt validator app wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=a82e4bc58ed4ed776e914cf04b48b24be42498f8531a7f070e013d01ba7e4c2d

```text
.ce/changelog/ce103-s2-posture.md
.ce/pr-manifests/ce103-s2-posture.md
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_openshell_ring1_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
