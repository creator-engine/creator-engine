# PR path manifest - ce23-s1-baseline-attestation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce23-s1-baseline-attestation
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#23 Slice 1 only: G-C brownfield baseline-attestation record. This slice
adds the value-free schema, a pure deterministic record builder, one registered
validator check, red-to-green tests, and a changelog fragment. It does not
build G-A capture planning or G-B scrub wiring.

Base:
`05b94bef27db10116c04d8b93d7e14eb3c83a3c8` (`origin/main` after ce-ops#158 / #294).

Per-file purpose (closed path-set - 16 paths):

- **`.ce/changelog/ce23-s1-baseline-attestation.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce23-s1-baseline-attestation.md`** *(A)* - this PR's closed path-set carrier.
- **`schemas/brownfield-baseline-attestation.schema.yaml`** *(A)* - value-free baseline-attestation schema.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated build identity for the rebased source tree.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the new validator check.
- **`validators/creator_engine_validator/checks/brownfield_baseline_attestation.py`** *(A)* - schema, secret-shape, and content-digest validator.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure deterministic baseline-attestation record builder.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_brownfield_baseline_attestation.py`** *(A)* - Slice 1 schema, builder, and check regression tests.
- **`validators/tests/unit/test_change_status.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_merge.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_open_change.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_redact.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - registered-check count drift guard updated.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=4707955e09b6500210716f48602984127c772a785be4e170152649baa045e8f2

```text
.ce/changelog/ce23-s1-baseline-attestation.md
.ce/pr-manifests/ce23-s1-baseline-attestation.md
schemas/brownfield-baseline-attestation.schema.yaml
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/brownfield_baseline_attestation.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_brownfield_baseline_attestation.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
