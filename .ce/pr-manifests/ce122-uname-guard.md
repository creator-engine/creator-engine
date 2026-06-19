# PR path manifest - ce122-uname-guard - guard installer uname test overrides

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce122-uname-guard

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#122 on 2026-06-18: harden the public installer so
`CE_TEST_UNAME_S` / `CE_TEST_UNAME_M` cannot bypass the real platform gate unless
the installer is running under explicit test mode. Commit locally only; do not
push.

Base:
`51c9dace33147395a48bcec67bf145bf728abc39` (`origin/main` at branch creation).

The changes:
- `docs/install.sh` refuses `CE_TEST_UNAME_S` / `CE_TEST_UNAME_M` with
  `test_override_refused` unless `CE_INSTALLER_TEST_MODE=1` is present.
- Platform override values are only read inside explicit test mode; real installs
  always read `uname -s` / `uname -m`.
- Installer integration tests cover fail-closed real-install refusal before any
  network fetch and update existing platform-selection tests to opt into test
  mode.

Per-file purpose (the closed path-set - 6 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce122-uname-guard.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce122-uname-guard.md`** *(A)* - this carrier.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - re-pinned `install.sh` entry
  (c5ccc3af -> 8f60bb5b) for the uname-guard change.
- **`docs/install.sh`** *(M)* - fail-closed guard and test-mode-only platform overrides.
- **`docs/llms-install.md`** *(M)* - re-pinned `sha256s_sha256` + `content_sha256`
  and re-signed canonical bytes with `ce-root-v1` (SSHSIG `ce-spec-v1`).
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - red/green
  coverage for refusal and explicit test-mode platform selection.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=db428b5714de19c2f4109c7788a063c7e5e77ccc2f3d91b8907ecae014346ba8

```text
.ce/changelog/ce122-uname-guard.md
.ce/pr-manifests/ce122-uname-guard.md
docs/downloads/0.2.0/SHA256SUMS
docs/install.sh
docs/llms-install.md
validators/tests/integration/test_install_bootstrap.py
```
