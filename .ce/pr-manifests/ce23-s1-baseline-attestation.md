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
validator check, red-to-green tests, changelog fragment, and rebuilt validator
app wheel. It does not build G-A capture planning or G-B scrub wiring.

Base:
`4693465d8760bad13ccfa230cc9b17022092e71f` (`origin/main` at branch cut).

Per-file purpose (closed path-set - 17 paths):

- **`.ce/changelog/ce23-s1-baseline-attestation.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce23-s1-baseline-attestation.md`** *(A)* - this PR's closed path-set carrier.
- **`schemas/brownfield-baseline-attestation.schema.yaml`** *(A)* - value-free baseline-attestation schema.
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
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=24266ea87d0eb0fa99c401c8467726ba8f5c57dac0d999f343a2a97fc8873238

```text
.ce/changelog/ce23-s1-baseline-attestation.md
.ce/pr-manifests/ce23-s1-baseline-attestation.md
schemas/brownfield-baseline-attestation.schema.yaml
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
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
