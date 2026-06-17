# PR path manifest - ce109-s8c-landlock-cred-deny - Ring-1 Section-8c filesystem mediation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce109-s8c-landlock-cred-deny

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified BUILD MANDATE (ce-ops#109, latest comment) — Ring-1 Section-8c
filesystem mediation (Landlock credential-path read-deny). Build seat (dev-3)
commits locally and holds; no push, PR, or issue mutation.

Base:
`2f3d2b0c84bcca54b3ebfe27762624ab1ecf24ab` (`origin/main` after the #249
post-#248 rebase).

The changes (ce-ops#109 Section-8c):
- Hoists the credential-shape predicate `is_secret_path` (+ its rule constants)
  out of v1 `hook_check` into a new **shared** module `secret_paths`, so the v3
  runner reuses the same single source of truth without a v1↔v3 boundary
  crossing. `hook_check.is_secret_path` is re-exported unchanged.
- Adds the shared `fs_mediation` module: a Landlock read-confinement applied to
  the runner subprocess at launch via `preexec_fn` (`no_new_privs` +
  `landlock_restrict_self`). It grants `READ_FILE` only beneath an explicit
  allow-list (system runtime roots + workspace); credential stores outside it
  (`~/.ssh`, `~/.aws`, `~/.netrc`, `~/.git-credentials`, out-of-workspace
  `.env`) are kernel-denied. Reuses `is_secret_path` as a fail-closed config
  guard. Honest fallback: fail-closed when Section-8c is required and Landlock is
  unavailable; otherwise an advisory `sandbox_fs_enforced=false` capability that
  never falsely claims FS mediation, with the non-coverage explicitly declared.
- Wires the real runner launch paths: `ring1_tool_guard.build_runtime` now builds
  `RunnerFsConfinement`, resolves the required Landlock capability, and carries
  `landlock_preexec`; `openshell_backend.run` passes that hook through
  `exec_sandbox`, and the live OpenShell CLI client forwards it to
  `subprocess.run` before user code execs. A host without Landlock fails closed
  before sandbox creation where Section-8c is required.
- Composes caller-supplied `preexec_fn` with Landlock first under
  `run_confined`, so a caller hook cannot disable enforcement or read
  out-of-workspace credentials before exec.
- Extends credential-shape coverage to `.ce-keys`, `github_token`, and `*_token`
  basenames.
- Tests cover both directions: a launched confinement DENIES out-of-workspace
  `.env` / `~/.ssh/id_rsa` / `~/.aws/credentials` reads while ALLOWING
  in-workspace source reads and `git status`/`git add`; the in-workspace `.env`
  residual is proven and declared; a caller-supplied `preexec_fn` cannot read the
  exact out-of-workspace `.env`; the unavailable path fails closed and emits
  `sandbox_fs_enforced=false`. The live proof is gated on real Landlock
  availability; host-portable unit tests cover the rest, including OpenShell hook
  handoff and the added credential-shape rules.
- The validator app wheel is rebuilt from the current source and
  `validators/wheelhouse/SHA256SUMS` is refreshed. New app-wheel digest:
  `d81c646c5ef7f3ba73569e1aaa34c9280ab8c82579927a9697036d66149707e1`.

Per-file purpose (the closed path-set - 16 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce109-s8c-landlock-cred-deny.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce109-s8c-landlock-cred-deny.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/fs_mediation.py`** *(A)* - the Section-8c
  Landlock read-confinement mechanism, capability declaration, preexec
  composition, and honest fail-closed/advisory fallback.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - re-export
  `is_secret_path` from the shared `secret_paths` module (single source of truth;
  public API unchanged).
- **`validators/creator_engine_validator/runner/openshell_backend.py`** *(M)* -
  carry the runtime Landlock preexec hook through `run` -> `exec_sandbox` -> live
  CLI subprocess launch, and fail closed before sandbox creation when required.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* -
  build the Section-8c runtime confinement/capability in `build_runtime`, include
  runner scratch/runtime read roots, and expose the `landlock_preexec` hook.
- **`validators/creator_engine_validator/secret_paths.py`** *(A)* - shared
  credential-path predicate extracted from `hook_check`, including `.ce-keys` and
  token basename coverage.
- **`validators/tests/integration/test_fs_mediation_landlock.py`** *(A)* - live
  both-direction Landlock deny/allow, caller-preexec `.env` deny regression, and
  git regression proof (availability-gated).
- **`validators/tests/integration/test_runner_ring1_codex_push.py`** *(M)* -
  local OpenShell-style runner integration now accepts/applies the runtime
  preexec hook while preserving PATH-shim git/gh behavior.
- **`validators/tests/unit/test_fs_mediation.py`** *(A)* - capability shapes,
  fail-closed/advisory fallback, preexec composition, config-guard, ABI-probe
  unit coverage.
- **`validators/tests/unit/test_openshell_backend.py`** *(M)* - fake-client
  coverage that OpenShell `run` passes a preexec hook.
- **`validators/tests/unit/test_openshell_ring1_guard.py`** *(M)* - guard
  lifecycle coverage for OpenShell preexec handoff and unavailable-host
  fail-closed behavior before sandbox creation.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(M)* - runtime
  descriptor tests for required Landlock hook, allow roots, and unavailable-host
  fail-closed behavior.
- **`validators/tests/unit/test_secret_paths.py`** *(A)* - extraction parity +
  predicate classification coverage for credential/token shapes.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - rebuilt-wheel digest.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* -
  rebuilt validator app wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=850a8caae6f196c25c5a5864abe77cf5d642e7eb3a23e19341cd113ddd0dc5b0

```text
.ce/changelog/ce109-s8c-landlock-cred-deny.md
.ce/pr-manifests/ce109-s8c-landlock-cred-deny.md
validators/creator_engine_validator/fs_mediation.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/creator_engine_validator/secret_paths.py
validators/tests/integration/test_fs_mediation_landlock.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/unit/test_fs_mediation.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_openshell_ring1_guard.py
validators/tests/unit/test_runner_ring1_tool_guard.py
validators/tests/unit/test_secret_paths.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
