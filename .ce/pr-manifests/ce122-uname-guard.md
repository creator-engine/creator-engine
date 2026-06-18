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

Per-file purpose (the closed path-set - 4 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce122-uname-guard.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce122-uname-guard.md`** *(A)* - this carrier.
- **`docs/install.sh`** *(M)* - fail-closed guard and test-mode-only platform overrides.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - red/green
  coverage for refusal and explicit test-mode platform selection.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b40c20a4711b8023bc9b3848468d372efcb4f2a1d84d6727c994cf4144bf5293

```text
.ce/changelog/ce122-uname-guard.md
.ce/pr-manifests/ce122-uname-guard.md
docs/install.sh
validators/tests/integration/test_install_bootstrap.py
```
