# PR path manifest - ce197-profile-path

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce197-profile-path
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`4956994d1731185fa8fcf76c265caea250ad5cfe` (`origin/main` at branch handoff).

- **Declared work class:** tiny

Scope:
ce-ops#197 PR-3 profile-PATH standardization writer. The slice adds an
idempotent CE-marked shell-profile PATH block writer, wires the bootstrap
installer to run it by default, and preserves an explicit `--no-fix-path`
opt-out. It intentionally does not republish or re-sign the frozen 0.2.0
download mirror.

Per-file purpose:
- **`.ce/changelog/ce197-profile-path.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce197-profile-path.md`** *(A)* - this closed path-set carrier.
- **`docs/install.sh`** *(M)* - bootstrap installer default-on PATH block wiring plus `--no-fix-path`.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify `ce_profile_path.py` as v1.
- **`validators/creator_engine_validator/ce_profile_path.py`** *(A)* - CE-marked profile PATH block writer and small CLI.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - bootstrap coverage for default-on profile update and opt-out.
- **`validators/tests/unit/test_ce_profile_path.py`** *(A)* - unit coverage for add-once, no-op rerun, non-CE preservation, and marker replacement.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* - keep the frozen 0.2.0 mirror self-consistency check scoped to versioned mirror files so source installer edits do not imply an unsigned republish.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - v1 taxonomy count ratchet for the new module.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=d3b893032bf9f36cd1362b308fdee709e0fa5db7a153fab0b2a8731634f0d740

```text
.ce/changelog/ce197-profile-path.md
.ce/pr-manifests/ce197-profile-path.md
docs/install.sh
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_profile_path.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_ce_profile_path.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_version_boundary.py
```
