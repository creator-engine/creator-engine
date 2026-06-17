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
`64678daf0376c0b3ef227b63c8a00fc6d6766f4e` (`origin/main` at branch creation;
PR #248 "Ring-1 Section-8 S2 posture-pin" merge).

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
- Scope is the runner subprocess only; the deployed-Claude/controller path and
  the OpenShell/gVisor backends are untouched.
- Tests cover both directions: a launched confinement DENIES out-of-workspace
  `.env` / `~/.ssh/id_rsa` / `~/.aws/credentials` reads while ALLOWING
  in-workspace source reads and `git status`/`git add`; the in-workspace `.env`
  residual is proven and declared; the unavailable path fails closed and emits
  `sandbox_fs_enforced=false`. The live proof is gated on real Landlock
  availability; host-portable unit tests cover the rest.
- The validator app wheel is rebuilt from the current source and
  `validators/wheelhouse/SHA256SUMS` is refreshed. New app-wheel digest:
  `1299a4769cf42678d5d780923e394f5de0e19cf555a8a5b7ed0fc986e1b1ee84`.

Per-file purpose (the closed path-set - 10 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce109-s8c-landlock-cred-deny.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce109-s8c-landlock-cred-deny.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/fs_mediation.py`** *(A)* - the Section-8c
  Landlock read-confinement mechanism, capability declaration, and honest
  fail-closed/advisory fallback.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - re-export
  `is_secret_path` from the shared `secret_paths` module (single source of truth;
  public API unchanged).
- **`validators/creator_engine_validator/secret_paths.py`** *(A)* - shared
  credential-path predicate extracted from `hook_check`.
- **`validators/tests/integration/test_fs_mediation_landlock.py`** *(A)* - live
  both-direction Landlock deny/allow + git regression proof (availability-gated).
- **`validators/tests/unit/test_fs_mediation.py`** *(A)* - capability shapes,
  fail-closed/advisory fallback, config-guard, ABI-probe unit coverage.
- **`validators/tests/unit/test_secret_paths.py`** *(A)* - extraction parity +
  predicate classification coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - rebuilt-wheel digest.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* -
  rebuilt validator app wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=fe5b280c9b0b08a032c0bf20e901d46a717ff2435dec370e72b9a8494134712f

```text
.ce/changelog/ce109-s8c-landlock-cred-deny.md
.ce/pr-manifests/ce109-s8c-landlock-cred-deny.md
validators/creator_engine_validator/fs_mediation.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/secret_paths.py
validators/tests/integration/test_fs_mediation_landlock.py
validators/tests/unit/test_fs_mediation.py
validators/tests/unit/test_secret_paths.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
