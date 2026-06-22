# PR Path Manifest - ce162-seat-ops-ssot

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce162-seat-ops-ssot
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#162 operator seat operations SSOT. This adds one authoritative
Claude/Codex seat launch/governance/containment runbook, a pure registered
validator check that keeps the runbook's refusal clause table synchronized with
the launcher spec modules, focused unit coverage, and the registered-check count
updates caused by the new check. GitHub workflow changes, live provider calls,
credential changes, hosted authority, and launcher behavior changes are out of
scope.

Per-file purpose (closed path-set - 14 paths):
- **`.ce/changelog/ce162-seat-ops-ssot.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce162-seat-ops-ssot.md`** *(A)* - this carrier.
- **`docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`** *(A)* - authoritative operator runbook with the synced refusal clause table.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - registers the runbook sync check.
- **`validators/creator_engine_validator/checks/operator_runbook_refusal_sync.py`** *(A)* - pure check deriving expected clauses from launcher spec constants.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_change_status.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_merge.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_open_change.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_operator_runbook_refusal_sync.py`** *(A)* - focused unit tests for registration and clause sync failures.
- **`validators/tests/unit/test_redact.py`** *(M)* - registered-check count drift guard updated.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - registered-check count drift guard updated.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=f26c8373506f09680b19256a4343e9501bcce4dc3852c048ccb1561e0f549d81

```text
.ce/changelog/ce162-seat-ops-ssot.md
.ce/pr-manifests/ce162-seat-ops-ssot.md
docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/operator_runbook_refusal_sync.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_operator_runbook_refusal_sync.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
