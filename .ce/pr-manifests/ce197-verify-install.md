# PR path manifest - ce197-verify-install - ce-ops#197 verify install provenance

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce197-verify-install

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
User brief for ce-ops#197 PR-1 — add `ce verify-install` as a post-install
provenance verifier for genuine, untampered CE releases.

The changes:
- Add `ce verify-install [--json] [--install-root PATH] [--offline]`.
- Verify install-state pins, installed venv bytes via wheel RECORD metadata, and
  online live `SHA256SUMS`; degrade to local-only in `--offline`.
- Keep bootstrap manifest parsing single-source by extracting the existing
  `v3_installer` parser into a shared module reused by both call sites.
- Update docs inventory, v1 docs reconciliation, and version-boundary taxonomy.

Per-file purpose (the closed path-set - 11 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce197-verify-install.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce197-verify-install.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - document `ce verify-install` in the v1 command inventory.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify `ce_provenance` as v1.
- **`validators/creator_engine_validator/bootstrap_manifest.py`** *(A)* - shared single-source bootstrap manifest parser.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - add `verify-install` parser and dispatch.
- **`validators/creator_engine_validator/ce_provenance.py`** *(A)* - post-install provenance verifier.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - delegate bootstrap parser API to shared parser.
- **`validators/tests/unit/test_ce_provenance.py`** *(A)* - TDD coverage for pass/refuse/offline/missing-state/CLI JSON.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - expected command inventory includes `verify-install`.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - v1 runtime count reflects `ce_provenance`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=f7a9cf236e7de49dcb3c354900e40c9715ca11e2445fb38277982e7702a93683

```text
.ce/changelog/ce197-verify-install.md
.ce/pr-manifests/ce197-verify-install.md
README.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/bootstrap_manifest.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_provenance.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_ce_provenance.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
