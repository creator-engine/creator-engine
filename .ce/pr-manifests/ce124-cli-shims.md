# PR path manifest - ce124-cli-shims - installer user-local CLI shims

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base 02c3f0d --manifest-dir .ce/pr-manifests --head-ref ce124-cli-shims

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#124 on 2026-06-18: fix the installer CLI exposure
step so post-install `cev3` and `ce` shims exist under `~/.local/bin`, resolve to
the verified venv entrypoints, and warn when `~/.local/bin` is not on `PATH`.
Commit locally only; do not push. Do not touch `docs/downloads/`.

Base:
`02c3f0d` (`origin/main` at branch creation).

The changes:
- `docs/install.sh` now creates or repairs `~/.local/bin/cev3` and
  `~/.local/bin/ce` after the verified venv is healthy, replacing stale symlinks
  but refusing to overwrite non-symlink files.
- The installer emits a clear warning when `~/.local/bin` is not in the current
  `PATH`.
- `docs/contracts/installer.md` documents the E1 user-local shim behavior
  without changing the signed `docs/llms-install.md` spec.
- Bootstrap integration coverage proves fresh install and idempotent rerun leave
  both shims present and resolving to the venv entrypoints.

Per-file purpose (the closed path-set - 7 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce124-cli-shims.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce124-cli-shims.md`** *(A)* - this carrier.
- **`docs/contracts/installer.md`** *(M)* - updates the unsigned installer
  contract for E1 user-local shim creation and PATH warning behavior.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - re-pinned `install.sh` entry
  (8f60bb5b -> 0e8c53a4) for the shim-creation change.
- **`docs/install.sh`** *(M)* - creates idempotent `cev3` and `ce` user-local
  shims after verified venv health checks.
- **`docs/llms-install.md`** *(M)* - re-pinned `sha256s_sha256` + `content_sha256`
  and re-signed canonical bytes with `ce-root-v1` (SSHSIG `ce-spec-v1`).
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - failing
  regression first; now asserts shim existence, target resolution, rerun
  idempotence, and PATH warning.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=bb562e1800e9110a6e330a21d98a868130164df7a4db5657167cda3f0d4e7414

```text
.ce/changelog/ce124-cli-shims.md
.ce/pr-manifests/ce124-cli-shims.md
docs/contracts/installer.md
docs/downloads/0.2.0/SHA256SUMS
docs/install.sh
docs/llms-install.md
validators/tests/integration/test_install_bootstrap.py
```
