# PR path manifest - ce260-release-artifact-parity-guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce260-release-artifact-parity-guard --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#260 adds an offline release artifact parity guard and refreshes the
0.2.0 mirrored installer so the served installer, release-local installer, and
`SHA256SUMS` entry agree.

Note:
Re-signing `docs/llms-install.md` requires the held `ce-root-v1` key and is
controller work. This PR only flags that follow-up in the changelog.

Per-file purpose:
- **`.ce/changelog/ce260-release-artifact-parity-guard.md`** *(A)* - changelog fragment, including the controller-only signing note.
- **`.ce/pr-manifests/ce260-release-artifact-parity-guard.md`** *(A)* - this closed path-set carrier.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - refreshed `install.sh` digest.
- **`docs/downloads/0.2.0/install.sh`** *(M)* - regenerated from `docs/install.sh`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the new check in the offline gate.
- **`validators/creator_engine_validator/checks/release_artifact_parity_guard.py`** *(A)* - release installer parity validator.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_change_status.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_merge.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_open_change.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_redact.py`** *(M)* - updates the registry-count invariant for the new check.
- **`validators/tests/unit/test_release_artifact_parity_guard.py`** *(A)* - focused unit coverage for the parity guard.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - updates the registry-count invariant for the new check.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=6c44da3da949b2e717488145da42246c0cdeda380b8a32f40e4237ddc36ffc6e

```text
.ce/changelog/ce260-release-artifact-parity-guard.md
.ce/pr-manifests/ce260-release-artifact-parity-guard.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/install.sh
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/release_artifact_parity_guard.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_release_artifact_parity_guard.py
validators/tests/unit/test_version_boundary.py
```
