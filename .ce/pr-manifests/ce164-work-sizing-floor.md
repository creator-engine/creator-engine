# PR path manifest - ce164-work-sizing-floor

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce164-work-sizing-floor
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#164/#170 G5 Work-sizing F2: classifier plus deterministic floor check
and PR-diff enforcement.
This lands a new registered `work_sizing_floor` validator check beside the F1
`work_sizing` ceremony check, with local generated/lockfile/vendored exclusions,
a pure git `--numstat` parser, a schema for persisted floor records, a
`verify-work-sizing-floor` CLI gate, and focused offline tests. Explicitly
excluded: wheel rebuild, Frame-to-Shape UX, dispatch, datastore, or F1
record-shape changes.

Per-file purpose (closed path-set - 15 paths):

- **`.ce/changelog/ce164-work-sizing-floor.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce164-work-sizing-floor.md`** *(A)* - this PR's closed path-set carrier.
- **`schemas/work-sizing-floor.schema.yaml`** *(A)* - schema for persisted floor records.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the `work_sizing_floor` check.
- **`validators/creator_engine_validator/checks/work_sizing_floor.py`** *(A)* - numstat parser/classifier, deterministic floor record check, and PR-diff gate.
- **`validators/creator_engine_validator/cli.py`** *(M)* - adds `verify-work-sizing-floor`.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_change_status.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_merge.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_open_change.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_redact.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_work_sizing_floor.py`** *(A)* - parser/classifier/check tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=e17add2bc5262f3be5f7f836b87b19b754ea22513a4d6e9c775c687d04733c4a

```text
.ce/changelog/ce164-work-sizing-floor.md
.ce/pr-manifests/ce164-work-sizing-floor.md
schemas/work-sizing-floor.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/work_sizing_floor.py
validators/creator_engine_validator/cli.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_work_sizing_floor.py
```
