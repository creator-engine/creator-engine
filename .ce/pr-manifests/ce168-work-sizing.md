# PR path manifest — ce-ops#168 (work-sizing ceremony F1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce168-work-sizing
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count
and SHA256 to match the fenced block.

Ratified scope:
F1 of ce-ops#168, based on the couriered work-sizing journey design
`tmp/work-sizing-journey-design.md` (sha256
`625c3aec1ec06e4d36141617cbf77cd264dd047b199c75cae2267cc2b9a4af70`) and
the F1 implementation brief `tmp/f1-worksizing-feature.md` (sha256
`71511e67406adf7dec9d0584db0e054cd3414b4ba2ab698ea328fe81b0b4c709`).

Scope: build only the CI-pure thin slice: `size_ceremony(work_class,
mutation_class)`, `schemas/work-sizing.schema.yaml`, a seed validator check, and
red-to-green tests. Explicitly excluded: classifier, #164 deterministic floor,
Frame→Shape UX, dispatch, datastore, cockpit rendering, and merge-gate recheck.

Per-file purpose:
- **`.ce/changelog/ce168-work-sizing.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce168-work-sizing.md`** *(A)* — this carrier
  (self-inclusive).
- **`schemas/work-sizing.schema.yaml`** *(A)* — sizing-record schema.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* —
  registers the seed `work_sizing` check.
- **`validators/creator_engine_validator/checks/work_sizing.py`** *(A)* —
  schema validation check for `kind: sizing-record`.
- **`validators/creator_engine_validator/work_sizing.py`** *(A)* — pure
  A.4 size/risk ceremony mapping.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_change_status.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* —
  registered-check count drift guard updated.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* — registered-check
  count drift guard updated.
- **`validators/tests/unit/test_merge.py`** *(M)* — registered-check count drift
  guard updated.
- **`validators/tests/unit/test_open_change.py`** *(M)* — registered-check count
  drift guard updated.
- **`validators/tests/unit/test_redact.py`** *(M)* — registered-check count drift
  guard updated.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* —
  registered-check count drift guard updated.
- **`validators/tests/unit/test_work_sizing.py`** *(A)* — pure ceremony and A.4
  table tests.
- **`validators/tests/unit/test_work_sizing_check.py`** *(A)* — seed check tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned app-wheel checksum
  after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* — rebuilt app wheel matching this branch's validator source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=3e49a7c304d4a1fb043dced71c67871f94e8f0192ddd1b259f5321cce9551a18

```text
.ce/changelog/ce168-work-sizing.md
.ce/pr-manifests/ce168-work-sizing.md
schemas/work-sizing.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/work_sizing.py
validators/creator_engine_validator/work_sizing.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_work_sizing.py
validators/tests/unit/test_work_sizing_check.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
